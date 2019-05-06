#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the `openedx-blockstore-relay` transfer_data module.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json

import mock
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from .course_data import TestCourseMixin
from .xml_test_mixin import XmlTestMixin
from ..transfer_data import transfer_to_blockstore


class TransferToBlockstoreTestCase(TestCourseMixin, XmlTestMixin, ModuleStoreTestCase):
    """
    Tests for the relay's transfer_data code, which transfers serialized OLX
    data to Blockstore.
    """
    # pylint: disable=no-member
    maxDiff = None
    COLLECTION_UUID = 'd3e311a8-b3a8-439d-a111-cc6cb99790e8'
    BUNDLE_UUID = '93fc9c6e-4249-4d57-a63c-b08be9f4fe02'
    DRAFT_UUID = '12345678-4249-4d57-a63c-a12354565756'

    def setUp(self):
        super(TransferToBlockstoreTestCase, self).setUp()

        # Mock out blockstore:
        for mocked_fn in ('create_bundle', 'create_draft', 'add_file_to_draft', 'commit_draft'):
            patcher = mock.patch('openedx_blockstore_relay.transfer_data.{}'.format(mocked_fn))
            setattr(self, 'mock_' + mocked_fn, patcher.start())
            self.addCleanup(patcher.stop)
        self.mock_create_bundle.return_value = {"uuid": self.BUNDLE_UUID}
        self.mock_create_draft.return_value = {"uuid": self.DRAFT_UUID}

    def test_transfer_to_blockstore(self):
        """
        Test the whole workflow of exporting part of a course to Blockstore,
        though with Blockstore itself mocked out.
        """
        block_key = self.course.id.make_usage_key('vertical', 'unit1_1_2')
        transfer_to_blockstore(block_key)

        self.mock_create_bundle.assert_called_once()
        self.mock_create_draft.assert_called_once()
        self.mock_commit_draft.assert_called_once()

        # Check the files that were uploaded (via add_file_to_draft(draft_id, name, data)):
        files_posted = set([call[0][1] for call in self.mock_add_file_to_draft.call_args_list])

        self.assertSetEqual(files_posted, {
            'bundle.json',
            'unit/unit1_1_2/definition.xml',
            'html/html_b/definition.xml',
            'html/html_b/static/html_b.html',
            'html/html_b/static/sample_handout.txt',
            'video/video_b/definition.xml',
            'video/video_b/static/50ce37bf-594a-425c-9892-6407a5083eb3-en.srt',
            'drag-and-drop-v2/dnd/definition.xml',
        })

        file_data_by_path = {call[0][1]: call[0][2] for call in self.mock_add_file_to_draft.call_args_list}

        self.assertXmlEqual(file_data_by_path['unit/unit1_1_2/definition.xml'], '''
            <unit display_name="Unit 1.1.2">
                <xblock-include definition="html/html_b"/>
                <xblock-include definition="video/video_b"/>
                <xblock-include definition="drag-and-drop-v2/dnd"/>
            </unit>
        ''', remove_comments=True)

        bundle_json_data = json.loads(file_data_by_path['bundle.json'])
        self.assertEqual(bundle_json_data['schema'], 0.1)
        self.assertEqual(bundle_json_data['type'], 'olx/unit')
        self.assertSetEqual(set(bundle_json_data['assets']), {
            'video/video_b/static/50ce37bf-594a-425c-9892-6407a5083eb3-en.srt',
            'html/html_b/static/html_b.html',
            'html/html_b/static/sample_handout.txt',
        })
        self.assertSetEqual(set(bundle_json_data['components']), {
            'video/video_b/definition.xml',
            'html/html_b/definition.xml',
            'unit/unit1_1_2/definition.xml',
            'drag-and-drop-v2/dnd/definition.xml',
        })

        self.assertXmlEqual(
            file_data_by_path['html/html_b/static/html_b.html'],
            '<p>Activate the ωμέγα 13! <a href="/static/sample_handout.txt">Instructions.</a></p>'
        )
