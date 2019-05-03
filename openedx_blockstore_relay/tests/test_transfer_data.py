#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the `openedx-blockstore-relay` transfer_data module.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from xml.dom import minidom

import edxval.api as edxval_api
import mock
import six

from xmodule.contentstore.content import StaticContent
from xmodule.contentstore.django import contentstore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import SampleCourseFactory

from ..transfer_data import TransferBlock
from .course_data import TEST_COURSE, VIDEO_B_SRT_TRANSCRIPT_DATA, VIDEO_B_VAL_DATA


class TransferBlockTestCase(ModuleStoreTestCase):
    """
    Tests for TransferBlock. Requires a running instance of edX Studio.
    """
    maxDiff = None
    COLLECTION_UUID = 'd3e311a8-b3a8-439d-a111-cc6cb99790e8'
    BUNDLE_UUID = '93fc9c6e-4249-4d57-a63c-b08be9f4fe02'

    def setUp(self):
        super(TransferBlockTestCase, self).setUp()

        self.course = SampleCourseFactory.create(block_info_tree=TEST_COURSE)
        # And upload the course static asssets:
        asset_key = StaticContent.compute_location(self.course.id, 'sample_handout.txt')
        content = StaticContent(asset_key, "Fake asset", "application/text", "test".encode('utf8'))
        contentstore().save(content)
        # And the video data + transcript must also be stored in edx-val for the video export to work:
        edxval_api.create_video(VIDEO_B_VAL_DATA)
        edxval_api.create_video_transcript(**VIDEO_B_SRT_TRANSCRIPT_DATA)

    @mock.patch('openedx_blockstore_relay.transfer_data.requests')
    def test_transfer_to_blockstore(self, mock_requests):
        mock_response = mock.MagicMock()

        # TODO: Remove once _add_bundle_file() adds the path to the manifest without looking at the response.
        mock_response.json.return_value = {
            'path': '/unit1_1_2.olx',
        }
        mock_requests.post.return_value = mock_response

        block_key = self.course.id.make_usage_key('vertical', 'unit1_1_2')
        transfer_obj = TransferBlock(block_key)
        transfer_obj.transfer_block_to_bundle(self.BUNDLE_UUID)

        mock_requests.post.assert_called_once()
        call_kwargs = mock_requests.post.call_args[1]
        files_posted = set(call_kwargs['data']['path'])

        self.assertSetEqual(files_posted, {
            '/bundle.json',
            '/unit1_1_2.olx',
            '/unit1_1_2/html_b.html',
            '/unit1_1_2/50ce37bf-594a-425c-9892-6407a5083eb3-en.srt',  # the subtitles for video_b in unit1_1_2
            '/static/sample_handout.txt',
        })

        self.assertDictEqual(transfer_obj.manifest, {
            'assets': [
                '/static/sample_handout.txt',
            ],
            'components': ['/unit1_1_2.olx'],
            'dependencies': [],
            'schema': 0.1,
            'type': 'olx/unit',
        })

        file_data_by_path = {
            call_kwargs['data']['path'][idx]: call_kwargs['files'][idx][1][1]
            for idx in list(range(len(call_kwargs['files'])))  # files = [('data', (name, data, content_type)), ...]
        }

        self.assertXmlEqual(file_data_by_path['/unit1_1_2.olx'], '''
            <unit
                url_name="unit1_1_2"
                xmlns:block="http://code.edx.org/xblock/block" xmlns:option="http://code.edx.org/xblock/option"
            >
                <html display_name="Unicode and URL test" filename="html_b" url_name="html_b"/>
                <video
                    display_name="YouTube Video"
                    download_video="false"
                    edx_video_id="50ce37bf-594a-425c-9892-6407a5083eb3"
                    sub=""
                    transcripts="{&quot;en&quot;: &quot;50ce37bf-594a-425c-9892-6407a5083eb3-en.srt&quot;}"
                    url_name="video_b"
                    youtube_id_1_0="3_yD_cEKoCk"
                >
                    <video_asset client_video_id="A Video" duration="0.0" image="">
                        <transcripts>
                            <transcript file_format="srt" language_code="en" provider="Custom" />
                        </transcripts>
                    </video_asset>
                    <transcript language="en" src="50ce37bf-594a-425c-9892-6407a5083eb3-en.srt" />
                </video>
                <drag-and-drop-v2
                    url_name="dnd" display_name="A Drag and Drop Block (Pure XBlock)" xblock-family="xblock.v1"
                />
            </unit>
        ''')

        self.assertXmlEqual(
            file_data_by_path['/unit1_1_2/html_b.html'],
            '<p>Activate the ωμέγα 13! <a href="/static/sample_handout.txt">Instructions.</a></p>'
        )

    def assertXmlEqual(self, xml_str_a, xml_str_b):
        """
        Assert that the given XML strings are equal,
        ignoring attribute order and some whitespace variations.
        """
        def clean(xml_str):
            # Collapse repeated whitespace:
            xml_str = re.sub(r'(\s)\s+', r'\1', xml_str)
            if isinstance(xml_str, six.text_type):
                xml_str = xml_str.encode('utf8')
            return minidom.parseString(xml_str).toprettyxml()

        self.assertEqual(clean(xml_str_a), clean(xml_str_b))
