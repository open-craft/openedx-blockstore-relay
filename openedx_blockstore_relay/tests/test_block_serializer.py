#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the `openedx-blockstore-relay` transfer_data module.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from ..block_serializer import XBlockSerializer
from .. import compat
from .course_data import TestCourseMixin
from .xml_test_mixin import XmlTestMixin


class XBlockSerializerTestCase(TestCourseMixin, XmlTestMixin, ModuleStoreTestCase):
    """
    Tests for XBlockSerializer. Requires a running instance of edX Studio.
    """
    maxDiff = None

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
        Test serializing an HTML block
        """
        block_key = self.course.id.make_usage_key('html', 'html_b')
        result = XBlockSerializer(compat.get_block(block_key))

        self.assertEqual(result.orig_block_key, block_key)
        self.assertEqual(result.def_id, "html/html_b")
        self.assertEqual(len(result.static_files), 1)
        self.assertEqual(result.static_files[0].name, 'html_b.html')
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
