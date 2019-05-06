#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the `openedx-blockstore-relay` transfer_data module.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from .. import compat
from ..block_serializer import XBlockSerializer
from .course_data import TestCourseMixin
from .xml_test_mixin import XmlTestMixin


class XBlockSerializerTestCase(TestCourseMixin, XmlTestMixin, ModuleStoreTestCase):
    """
    Tests for XBlockSerializer. Requires a running instance of edX Studio.
    """
    maxDiff = None

    def test_sequential(self):
        """
        Test that when serializing a sequential/subsection, the children are
        referenced as <unit>, not <vertical>
        """
        block_key = self.course.id.make_usage_key('sequential', 'subsection1_1')
        result = XBlockSerializer(compat.get_block(block_key))
        self.assertXmlEqual(result.olx_str, """
            <sequential display_name="Subsection 1.1">
                <xblock-include definition="unit/unit1_1_1"/>
                <xblock-include definition="unit/unit1_1_2"/>
            </sequential>
            <!-- Imported from {block_key} using openedx-blockstore-relay -->
        """.format(block_key=block_key))

    def test_unit(self):
        """
        Test serializing a vertical (unit)
        """
        block_key = self.course.id.make_usage_key('vertical', 'unit1_1_2')
        result = XBlockSerializer(compat.get_block(block_key))

        self.assertEqual(result.orig_block_key, block_key)
        self.assertEqual(result.def_id, "unit/unit1_1_2")
        self.assertEqual(result.static_files, [])
        self.assertXmlEqual(result.olx_str, """
            <unit display_name="Unit 1.1.2">
                <xblock-include definition="html/html_b"/>
                <xblock-include definition="video/video_b"/>
                <xblock-include definition="drag-and-drop-v2/dnd"/>
            </unit>
            <!-- Imported from {block_key} using openedx-blockstore-relay -->
        """.format(block_key=block_key))

    def test_html(self):
        """
        Test serializing an HTML block that contains a reference to a
        contentstore static asset (an asset uploaded via Studio's "Files &
        Uploads" page)
        """
        block_key = self.course.id.make_usage_key('html', 'html_b')
        result = XBlockSerializer(compat.get_block(block_key))

        self.assertEqual(result.orig_block_key, block_key)
        self.assertEqual(result.def_id, "html/html_b")
        self.assertEqual(len(result.static_files), 2)
        self.assertEqual(result.static_files[0].name, 'html_b.html')
        self.assertEqual(result.static_files[1].name, 'sample_handout.txt')
        self.assertEqual(
            result.static_files[0].data,
            (
                '<p>Activate the ωμέγα 13! '
                '<a href="/static/sample_handout.txt">Instructions.</a></p>'
            ).encode('utf-8'),
        )
        self.assertXmlEqual(result.olx_str, """
            <html display_name="Unicode and URL test" filename="html_b"/>
            <!-- Imported from {block_key} using openedx-blockstore-relay -->
        """.format(block_key=block_key))

    def test_video(self):
        """
        Test serializing a video block and an associated transcript file.
        """
        block_key = self.course.id.make_usage_key('video', 'video_b')
        result = XBlockSerializer(compat.get_block(block_key))

        self.assertEqual(result.orig_block_key, block_key)
        self.assertEqual(result.def_id, "video/video_b")
        self.assertEqual(len(result.static_files), 1)
        self.assertEqual(result.static_files[0].name, '50ce37bf-594a-425c-9892-6407a5083eb3-en.srt')
        self.assertXmlEqual(result.olx_str, """
            <video
                display_name="YouTube Video" download_video="false"
                edx_video_id="50ce37bf-594a-425c-9892-6407a5083eb3" sub=""
                transcripts="{{&quot;en&quot;: &quot;50ce37bf-594a-425c-9892-6407a5083eb3-en.srt&quot;}}"
                youtube_id_1_0="3_yD_cEKoCk"
            >
                <video_asset client_video_id="video_b_123" duration="0.0" image="">
                    <transcripts>
                        <transcript file_format="srt" language_code="en" provider="Custom"/>
                    </transcripts>
                </video_asset>
                <transcript language="en" src="50ce37bf-594a-425c-9892-6407a5083eb3-en.srt"/>
            </video>
            <!-- Imported from {block_key} using openedx-blockstore-relay -->
        """.format(block_key=block_key))

    def test_problem(self):
        """
        Test serializing a problem block that contains a reference to a
        contentstore static imagae asset (an asset uploaded via Studio's "Files
        & Uploads" page)
        """
        block_key = self.course.id.make_usage_key('problem', 'problem_b')
        result = XBlockSerializer(compat.get_block(block_key))

        self.assertEqual(result.orig_block_key, block_key)
        self.assertEqual(result.def_id, "problem/problem_b")
        self.assertEqual(len(result.static_files), 1)
        self.assertEqual(result.static_files[0].name, 'edx.svg')
        self.assertIn('<svg', result.static_files[0].data)
        print(result.olx_str)
        print(compat.get_block(block_key).data)
        self.assertXmlEqual(result.olx_str, """
            <problem display_name="Pointing on a Picture" max_attempts="null">
                <p>Answer this question by clicking on the image below.</p>
                <imageresponse>
                    <imageinput src='/static/edx.svg' width='640' height='400' rectangle='(385,98)-(600,337)'/>
                </imageresponse>
                <solution>
                    <div class='detailed-solution'>
                        <p>Explanation here.</p>
                    </div>
                </solution>
            </problem>
            <!-- Imported from {block_key} using openedx-blockstore-relay -->
        """.format(block_key=block_key))
