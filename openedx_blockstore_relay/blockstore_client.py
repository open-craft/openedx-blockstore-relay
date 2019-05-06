"""
A very rudimentary API client for Blockstore
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import logging

import requests
import six
from django.conf import settings
from future.moves.urllib.parse import urljoin

log = logging.getLogger(__name__)


def encode_str_for_draft(input_str):
    """Given a string, return UTF-8 representation that is then base64 encoded."""
    if isinstance(input_str, six.text_type):
        input_str = input_str.encode('utf8')
    return base64.b64encode(input_str)


def create_bundle(collection_uuid, title, slug, **kwargs):
    """
    Create a bundle in the specified collection.
    """
    url = urljoin(settings.BLOCKSTORE_API_URL, 'bundles')
    data = dict(collection_uuid=str(collection_uuid), title=title, slug=slug, **kwargs)
    log.debug("POST %s %s", url, data)
    response = requests.post(url, data)
    response.raise_for_status()
    return response.json()


def create_draft(bundle_uuid, name, title):
    """
    Create a draft in the specified bundle.
    """
    url = urljoin(settings.BLOCKSTORE_API_URL, 'drafts')
    data = {'bundle_uuid': str(bundle_uuid), 'name': name, 'title': title, }
    log.debug("POST %s %s", url, data)
    response = requests.post(url, data)
    response.raise_for_status()
    return response.json()


def add_file_to_draft(draft_uuid, path, data):
    """
    Add the specified file data to the draft
    """
    url = urljoin(settings.BLOCKSTORE_API_URL, 'drafts/{}'.format(draft_uuid))
    log.debug("PATCH %s", url)
    response = requests.patch(url, json={'files': {path: encode_str_for_draft(data)}})
    response.raise_for_status()


def commit_draft(draft_uuid):
    """
    Commit the draft, saving the files to the Blockstore bundle.
    """
    url = urljoin(settings.BLOCKSTORE_API_URL, 'drafts/{}/commit'.format(draft_uuid))
    log.debug("POST %s", url)
    response = requests.post(url)
    response.raise_for_status()
