#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the `openedx-blockstore-relay` transfer_data module.
"""

from __future__ import absolute_import, unicode_literals


import ddt
import mock
from xml.etree import ElementTree

from django.test import TestCase
from opaque_keys.edx.keys import UsageKey
from xblock.core import XBlock

from openedx_blockstore_relay.transfer_data import TransferBlock, transfer_to_blockstore
from openedx_blockstore_relay.test_utils.compat import StubCompat, StaticContent


class TestXBlock(XBlock):
    """
    A simple XBlock for tests.
    """

    @property
    def url_name(self):
        return self.location.block_id

    def get_children(self):
        return getattr(self, 'children', [])

    def definition_to_xml(self, resource_fs):

        if self.location.block_type == 'poll':
            raise NotImplementedError()

        xml_object = ElementTree.Element(self.location.block_type)
        xml_object.set('display_name', "A test display name")
        return xml_object

@ddt.ddt
class TransferBlockTestCase(TestCase):
    """
    Tests for TransferBlock.
    """

    BLOCK_KEY = 'block-v1:edX+DemoX+Demo_Course+type@vertical+block@v1'

    INVALID_COLLECTION_UUID = 'invalid_bundle_uuid'
    INVALID_BUNDLE_UUID = 'invalid_bundle_uuid'

    COLLECTION_UUID = 'd3e311a8-b3a8-439d-a111-cc6cb99790e8'
    BUNDLE_UUID = '93fc9c6e-4249-4d57-a63c-b08be9f4fe02'

    def setUp(self):
        super(TransferBlockTestCase, self).setUp()

        self.block_key = UsageKey.from_string(self.BLOCK_KEY)
        self.block = TestXBlock(mock.MagicMock(), scope_ids=mock.MagicMock())
        self.block.location = self.block_key

        child_block_1 = TestXBlock(mock.MagicMock(), scope_ids=mock.MagicMock())
        child_block_1.location = UsageKey.from_string('block-v1:edX+DemoX+Demo_Course+type@html+block@html1')

        child_block_2 = TestXBlock(mock.MagicMock(), scope_ids=mock.MagicMock())
        child_block_2.location = UsageKey.from_string('block-v1:edX+DemoX+Demo_Course+type@poll+block@poll1')

        child_block_3 = TestXBlock(mock.MagicMock(), scope_ids=mock.MagicMock())
        child_block_3.location = UsageKey.from_string('block-v1:edX+DemoX+Demo_Course+type@video+block@video1')

        self.block.children = [child_block_1, child_block_2, child_block_3]

        self.compat = mock.patch('openedx_blockstore_relay.transfer_data.compat', StubCompat({
            self.block_key: self.block
        }, assets=[
            { 'content':StaticContent(''), 'path':'/static/one.jpeg'},
            { 'content':StaticContent('<script></script>'), 'path':'/static/one.js'},
        ], video_assets=[
            {'content':StaticContent('1. Hello welcome to this course.'), 'path': '/static/transcript.srt'},
        ]))
        self.compat.start()


    def test_bundle_creation(self):

        with mock.patch('openedx_blockstore_relay.transfer_data.requests') as mock_requests:
            with mock.patch('openedx_blockstore_relay.transfer_data.TransferBlock.transfer_block_to_bundle'):
                transfer_to_blockstore(self.block_key, collection_uuid=self.COLLECTION_UUID)

    def test_transfer_to_blockstore(self):

        with mock.patch('openedx_blockstore_relay.transfer_data.requests') as mock_requests:

            mock_response = mock.MagicMock()

            # TODO: Remove once _add_bundle_file() adds the path to the manifest without looking at the response.
            mock_response.json.return_value = {
                'path': '/vertical/v1.olx',
            }
            mock_requests.post.return_value = mock_response

            transfer_obj = TransferBlock(self.block_key)
            transfer_obj.transfer_block_to_bundle(self.BUNDLE_UUID)

            files_posted = set([call_args[1]['data']['path'] for call_args in mock_requests.post.call_args_list])

            self.assertSetEqual(files_posted, {
                '/bundle.json',
                '/vertical/v1.olx',
                '/video/video1.olx',
                '/html/html1.olx',
                '/static/one.jpeg',
                '/static/one.js',
                '/static/transcript.srt',
            })

            self.assertDictEqual(transfer_obj.manifest, {
                'assets': [
                    '/static/one.jpeg',
                    '/static/one.js',
                    '/static/one.jpeg',
                    '/static/one.js',
                    '/static/transcript.srt',
                    '/static/one.jpeg',
                    '/static/one.js'
                ],
                'components': ['/vertical/v1.olx'],
                'dependencies': [],
                'schema': 0.1,
                'type': u'olx/unit',
            })
