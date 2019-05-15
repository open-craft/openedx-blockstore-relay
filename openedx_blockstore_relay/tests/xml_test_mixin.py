"""
A mixin for working with XML in test cases
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from xml.dom import minidom

import six


class XmlTestMixin(object):
    """
    Mixin to provide test assertions about XML strings similarity
    """
    def assertXmlEqual(self, xml_str_a, xml_str_b, remove_comments=False):
        """
        Assert that the given XML strings are equal,
        ignoring attribute order and some whitespace variations.
        """
        def clean(xml_str):
            """ Parse + convert the given XML string to a consistent format """
            # Collapse repeated whitespace:
            xml_str = re.sub(r'(\s)\s+', r'\1', xml_str)
            if remove_comments:
                xml_str = re.sub(r'<!--.*?-->', '', xml_str, flags=re.MULTILINE)
            if isinstance(xml_str, six.text_type):
                xml_str = xml_str.encode('utf8')
            return minidom.parseString(xml_str).toprettyxml()

        self.assertEqual(clean(xml_str_a), clean(xml_str_b))
