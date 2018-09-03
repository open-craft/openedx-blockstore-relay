"""
Logic for transferring a subunit (aka XBlock, XModule) from Open edX to a Blockstore Bundle.
"""
from __future__ import absolute_import, print_function, unicode_literals

import json
import logging
import os
from xml.etree import ElementTree

import requests
from django.conf import settings
from django.utils.translation import gettext as _
from fs.errors import ResourceNotFound
from fs.memoryfs import MemoryFS
from fs.wrapfs import WrapFS
from future.moves.urllib.parse import urljoin

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

    def transfer_block_to_bundle(self, bundle_uuid):
        """
        Upload block-related files to the Bundle.
        """
        LOG.debug('Transfer %s to Bundle <%s>', self.block_key, bundle_uuid)
        self.bundle_files_url = urljoin(settings.BLOCKSTORE_API_URL,
                                        '/'.join(['bundles', str(bundle_uuid), 'files', '']))
        self.upload_olx(self.block)
        self.upload_manifest()

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
            'description': _("Transferred to Blockstore from Open edX {block_key}".format(block_key=self.block_key)),
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

    def upload_olx(self, block):
        """
        Upload the OLX for the given block definition, recursing through children.
        """
        block_key = block.location
        if block_key in self._block_olx_ok:
            # Prevent infinite recursion: don't re-create OLX for blocks that we've already done.
            return None

        block_type = block_key.block_type
        if block_type in ('course', 'chapter', 'sequential', 'vertical'):
            # Once we have a runtime, we can call `definition_to_xml` for these blocks too.
            olx_node = ElementTree.Element(block_type)
        else:
            try:
                filesystem = WrapFS(MemoryFS())
                olx_node = block.definition_to_xml(filesystem)
                self._upload_related_files(filesystem)
            except (NotImplementedError, AttributeError):
                LOG.warning("Block type not supported, skipping (%s)", block_key)
                self._block_olx_ok[block_key] = False
                return None
            except ResourceNotFound as exc:
                LOG.error("Error fetching block OLX (%s): %s", block_key, exc)
                self._block_olx_ok[block_key] = False
                return None

        for child in block.get_children():
            LOG.debug('Add child %s', child.location)
            self.upload_olx(child)
            if self._block_olx_ok[child.location]:
                # If we've successfully processed this child's OLX,
                # include a reference to the child in the parent block.
                child_ref = ElementTree.Element(child.location.block_type)
                child_ref.set('url_name', child.url_name)
                olx_node.append(child_ref)

        self._upload_olx(olx_node, block)
        self._block_olx_ok[block_key] = True
        return olx_node

    def upload_manifest(self, name='bundle.json', path=os.sep):
        """
        Upload the bundle manifest file.
        """
        return self._post_bundle_file(
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

    def _upload_asset(self, path, content):
        """
        Upload the static asset content to the bundle.
        """
        self.manifest['assets'].append(path)
        return self._post_bundle_file(
            path=path,
            data=content.data,
            content_type=content.content_type,
            public=True,
        )

    def _upload_related_files(self, filesystem):
        """
        Upload any files stored in the filesystem during OLX generation.

        Mostly (exclusively?) consists of `.html` files associated with HTML blocks, and so how we handle these needs to
        be determined per parent block type.
        """
        for item in filesystem.walk():
            for unit_file in item.files:
                file_path = os.path.join(item.path, unit_file.name)
                self._add_bundle_file(
                    path=item.path,
                    name=unit_file.name,
                    data=filesystem.open(file_path, 'rb'),
                )

    def _upload_olx(self, olx_node, block):
        """
        Upload the OLX file to the bundle.

        Share the block in the manifest "components" list if it's the top-level block.
        """
        block_key = block.location
        block_id = block_key.block_id
        block_type = block_key.block_type
        share_block = (block_key == self.block_key)
        response = self._add_bundle_file(
            path=os.path.join(os.sep, block_type),
            name='.'.join([block_id, 'olx']),
            data=ElementTree.tostring(olx_node, encoding="utf-8"),
            content_type=self._content_type(block_type),
            share_block=share_block,
            block=block,
        )
        return response

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

        response = self._post_bundle_file(data=data, path=path, name=name, content_type=content_type)
        if share_block:
            self.manifest['components'].append(response.json()['path'])

        self._upload_static_assets(data, block)
        return response

    def _post_bundle_file(self, data, path, name=None, content_type='application/octet-stream', public=False):
        """
        POST the given file to the Blockstore bundle.

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
        files = [('data', (name, data, content_type))]
        metadata = {
            'path': path,
            'public': public,
        }
        LOG.debug("POST file %s to %s...", metadata, self.bundle_files_url)
        response = requests.post(self.bundle_files_url, files=files, data=metadata)
        response.raise_for_status()
        return response

    def _upload_static_assets(self, data, block=None):
        """
        Collect and upload the static assets paths scraped from the given data string and block .
        """
        for asset in compat.collect_assets_from_text(data, self.block_key.course_key):
            self._upload_asset(**asset)

        if block and block.location.block_type == 'video':
            for asset in compat.collect_assets_from_video_block(block):
                self._upload_asset(**asset)
