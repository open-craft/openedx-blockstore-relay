"""
Logic for transferring a subunit (aka XBlock, XModule) from Open edX to a Blockstore Bundle.
"""
from __future__ import absolute_import, print_function, unicode_literals

import json
import logging
import os

import requests
from django.conf import settings
from django.utils.translation import gettext as _
from future.moves.urllib.parse import urljoin
from lxml.etree import Element, tostring as etree_tostring
from xblock.core import XML_NAMESPACES

from .adapters import override_export_fs, add_url_name_mixin
from . import compat

LOG = logging.getLogger(__name__)


def transfer_to_blockstore(block_key, bundle_uuid=None, collection_uuid=None):
    """
    Transfer the given block (and its children) to Blockstore.

    Args:
    * block_key: usage key of the Open edX block to transfer
    * bundle_uuid: UUID of the destination block
    * collection_uuid: UUID of the destination collection
      If no bundle_uuid provided, then a new bundle will be created here and that becomes the destination bundle.
    """
    transfer_obj = TransferBlock(block_key)
    if not bundle_uuid:
        bundle_uuid = transfer_obj.create_bundle(collection_uuid)
    transfer_obj.transfer_block_to_bundle(bundle_uuid)


class TransferBlock(object):
    """
    Transfers a single XBlock and its related files from Open edX to Blockstore.

    Uploads the sharable interface of the Bundle in a manifest bundle.json file.
    """

    BUNDLE_SCHEMA_VERSION = 0.1

    def __init__(self, block_key):
        """
        Store the block_key (UsageKey) and bundle_uuid (UUID).
        """
        super(TransferBlock, self).__init__()
        with add_url_name_mixin():  # Needed for pure XBlocks that do not inherit XModule export code
            self.block = compat.get_block(block_key)
        self.bundle_files_url = None
        self.manifest = {
            'schema': self.BUNDLE_SCHEMA_VERSION,
            'type': self._bundle_type(block_key.block_type),
            'assets': [],
            'components': [],
            'dependencies': [],
        }

        # Store the block_keys we've processed before, to prevent infinite recursion on Directed Acyclic Graphs (DAGs)
        self._block_olx_ok = {}

        self._reset_bundle_files_queue()

    def _reset_bundle_files_queue(self):
        """
        Initialize the queue of files to be uploaded to the bundle.
        """
        self._bundle_files_queue = {
            'files': [],
            'path': [],
            'public': [],
        }

    def transfer_block_to_bundle(self, bundle_uuid):
        """
        Upload block-related files to the Bundle.
        """
        LOG.debug('Transfer %s to Bundle <%s>', self.block_key, bundle_uuid)
        self.bundle_files_url = urljoin(settings.BLOCKSTORE_API_URL,
                                        '/'.join(['bundles', str(bundle_uuid), 'files', '']))
        self.prepare_olx(self.block)
        self.queue_manifest()
        self._post_bundle_files()

    def create_bundle(self, collection_uuid):
        """
        Create a new bundle on the given collection, and return its UUID.

        Use the given block to set the description, slug, and title of the new Bundle.
        """
        LOG.debug('Create new Bundle on Collection <%s>', collection_uuid)
        collection_url = urljoin(settings.BLOCKSTORE_API_URL, '/'.join(['collections', str(collection_uuid), '']))
        bundles_url = urljoin(settings.BLOCKSTORE_API_URL, '/'.join(['bundles', '']))
        data = {
            'collection': collection_url,
            'title': getattr(self.block, 'display_name', self.block_key),
            'slug': getattr(self.block, 'url_name', self.block_key.block_id),
            'description': _("Transferred to Blockstore from Open edX {block_key}").format(block_key=self.block_key),
        }
        LOG.debug("POST create bundle %s %s...", data, bundles_url)
        response = requests.post(bundles_url, data=data)
        response.raise_for_status()
        bundle_uuid = response.json()['uuid']
        LOG.info('Created bundle at %s', urljoin(bundles_url, bundle_uuid))
        return bundle_uuid

    @property
    def block_key(self):
        """
        Return the current block's usage key/location.
        """
        return self.block.location

    @property
    def block_files_prefix(self):
        """
        For a given unit, all non-public files other than the main OLX file
        should be in this "folder" within the bundle, e.g. /unit-first_unit/
        """
        return '/' + self.block_key.block_id + '/'

    def prepare_olx(self, block):
        """
        Prepare the OLX for the given XBlock/XModule and its children, and queue for upload.
        """
        block_key = block.location
        if block_key in self._block_olx_ok:
            # Prevent infinite recursion: don't re-create OLX for blocks that we've already done.
            return None

        olx_node = Element("root", nsmap=XML_NAMESPACES)  # The node name doesn't matter: add_xml_to_node will change it
        with override_export_fs(block) as filesystem:  # Needed for XBlocks that inherit XModuleDescriptor
            block.add_xml_to_node(olx_node)
            self._queue_related_files(filesystem)

        self.transform_olx(olx_node)

        self._queue_olx(olx_node, block)
        self._block_olx_ok[block_key] = True
        return olx_node

    def transform_olx(self, olx_node):
        """
        Apply transformations to the given OLX etree Node.

        Specifically, we convert the <vertical> tag to the
        <unit> tag, which is preferred for use in Blockstore.
        (Unit is more generic, has less tech debt, and is
        not coupled so tightly to the Open edX LMS runtime UI.)
        """
        for node in olx_node.iter():
            if node.tag == 'vertical':
                node.tag = 'unit'
                for key in node.attrib.keys():
                    if key not in ('display_name', 'url_name'):
                        LOG.warn('<vertical> tag attribute "%s" will be ignored after conversion to <unit>', key)

    def queue_manifest(self, name='bundle.json', path=os.sep):
        """
        Adds the bundle manifest file to the upload queue.
        """
        return self._queue_bundle_file(
            path=path,
            name=name,
            data=json.dumps(self.manifest, ensure_ascii=False),
            content_type='application/json',
        )

    @staticmethod
    def _bundle_type(block_type):
        """
        Return the manifest type to set for the given block_type.
        """
        if block_type in ['course']:
            bundle_type = 'course'
        elif block_type in ['chapter', 'sequential']:
            bundle_type = 'collection'
        else:
            bundle_type = 'unit'
        return 'olx/{}'.format(bundle_type)

    @staticmethod
    def _content_type(block_type):
        """
        Return the file content_type to set for the given block_type.
        """
        return 'olx/{}'.format(block_type)

    def _queue_asset(self, path, content):
        """
        Adds the static asset content to the upload queue.
        """
        self.manifest['assets'].append(path)
        return self._queue_bundle_file(
            path=path,
            data=content.data,
            content_type=content.content_type,
            public=True,
        )

    def _queue_related_files(self, filesystem):
        """
        Queues upload for any files stored in the filesystem during OLX generation.

        Examples of files this covers:
            - Video XModule exports transcripts as SRT files
              e.g. /course/static/50ce37bf-594a-425c-9892-6407a5083eb3-en.srt
            - HTML XModule saves its HTML content in a separate HTML file
              e.g. /html/197582986ce94c2aa62c673936091cb4.html
        """
        for item in filesystem.walk():
            for unit_file in item.files:
                file_path = os.path.join(item.path, unit_file.name)
                self._add_bundle_file(
                    path=self.block_files_prefix,
                    name=unit_file.name,
                    data=filesystem.open(file_path, 'rb'),
                )

    def _queue_olx(self, olx_node, block):
        """
        Adds the OLX file to the upload queue.

        Share the block in the manifest "components" list if it's the top-level block.
        """
        block_key = block.location
        block_id = block_key.block_id
        block_type = block_key.block_type
        share_block = (block_key == self.block_key)
        self._add_bundle_file(
            path='/',
            name='.'.join([block_id, 'olx']),
            data=etree_tostring(olx_node, encoding="utf-8", pretty_print=True),
            content_type=self._content_type(block_type),
            share_block=share_block,
            block=block,
        )

    def _add_bundle_file(self,
                         data,
                         path,
                         name=None,
                         content_type='application/octet-stream',
                         share_block=False,
                         block=None):
        """
        Add the given file data to the bundle.

        Scrape the static assets, and update the manifest if this is a shared file.
        """
        if hasattr(data, 'read'):
            # Read the data from the file pointer into a string so we can scrape it later
            data = data.read()

        path = self._queue_bundle_file(data=data, path=path, name=name, content_type=content_type)
        if share_block:
            self.manifest['components'].append(path)

        self._queue_static_assets(data, block)

    def _queue_bundle_file(self, data, path, name=None, content_type='application/octet-stream', public=False):
        """
        Queue the given file to be uploaded to the Blockstore bundle.

        Arguments:
        * data: string/byte data, or an open file pointer (required)
        * path: path to the file (required)
        * name: base file name, appended to path if provided (optional)
        * content_type: file content type (optional)
        * public: True if the file might need sharing on a CDN, default False.
        """
        if name is None:
            name = os.path.basename(path)
        else:
            path = os.path.join(path, name)
        if not data:
            # Empty files cause an error, so give it a space
            data = ' '

        LOG.debug("Queue file %s...", path)
        self._bundle_files_queue['files'].append(('data', (name, data, content_type)))
        self._bundle_files_queue['path'].append(path)
        self._bundle_files_queue['public'].append(public)
        return path

    def _queue_static_assets(self, data, block=None):
        """
        Collect and queue the static assets paths scraped from the given data string and block .
        """
        for asset in compat.collect_assets_from_text(data, self.block_key.course_key):
            self._queue_asset(**asset)

    def _post_bundle_files(self):
        """
        POST the queued files and metadata to the Blockstore bundle.
        """
        LOG.debug("POST %s files to %s...", len(self._bundle_files_queue['files']), self.bundle_files_url)
        response = None
        if self._bundle_files_queue['files']:
            response = requests.post(
                self.bundle_files_url,
                files=self._bundle_files_queue['files'],
                data={
                    'path': self._bundle_files_queue['path'],
                    'public': self._bundle_files_queue['public'],
                },
            )
            response.raise_for_status()
            self._reset_bundle_files_queue()
        return response
