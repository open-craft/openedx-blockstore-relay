"""
Code for serializing an XBlock to OLX
"""
from __future__ import absolute_import, print_function, unicode_literals
from collections import namedtuple
import os
import logging

from lxml.etree import Element, tostring as etree_tostring
import six

from .adapters import override_export_fs
from . import compat

log = logging.getLogger(__name__)

# A static file required by an XBlock
StaticFile = namedtuple('StaticFile', ['name', 'data'])


def blockstore_def_key_from_modulestore_usage_key(usage_key):
    """
    In modulestore, the "definition key" is a MongoDB ObjectID kept in split's
    definitions table, which theoretically allows the same block to be used in
    many places (each with a unique usage key). However, that functionality is
    not exposed in Studio (other than via content libraries). So when we import
    into Blockstore, we assume that each usage is unique, don't generate a usage
    key, and create a new "definition key" from the original usage key.

    So modulestore usage key
        block-v1:A+B+C+type@html+block@introduction
    will become Blockstore definition key
        html/introduction
    """
    block_type = usage_key.block_type
    if block_type == 'vertical':
        # We transform <vertical> to <unit>
        block_type = "unit"
    return block_type + "/" + usage_key.block_id


class XBlockSerializer(object):
    """
    This class will serialize an XBlock, producing:
        (1) A new definition ID for use in Blockstore
        (2) an XML string defining the XBlock and referencing the IDs of its
            children (but not containing the actual XML of its children)
        (3) a list of any static files required by the XBlock and their data
    """

    def __init__(self, block):
        """
        Serialize an XBlock to an OLX string + supporting files, and store the
        resulting data in this object.
        """
        self.orig_block_key = block.scope_ids.usage_id
        self.static_files = []
        self.def_id = blockstore_def_key_from_modulestore_usage_key(self.orig_block_key)

        # Create an XML node to hold the exported data
        olx_node = Element("root")  # The node name doesn't matter: add_xml_to_node will change it
        # ^ Note: We could pass nsmap=xblock.core.XML_NAMESPACES here, but the
        # resulting XML namespace attributes don't seem that useful?
        with override_export_fs(block) as filesystem:  # Needed for XBlocks that inherit XModuleDescriptor
            # Tell the block to serialize itself as XML/OLX:
            if not block.has_children:
                block.add_xml_to_node(olx_node)
            else:
                # We don't want the children serialized at this time, because
                # otherwise we can't tell which files in 'filesystem' belong to
                # this block and which belong to its children. So, temporarily
                # disable any children:
                children = block.children
                block.children = []
                block.add_xml_to_node(olx_node)
                block.children = children

            # Now the block/module may have exported addtional data as files in
            # 'filesystem'. If so, store them:
            for item in filesystem.walk():  # pylint: disable=not-callable
                for unit_file in item.files:
                    file_path = os.path.join(item.path, unit_file.name)
                    with filesystem.open(file_path, 'rb') as fh:
                        data = fh.read()
                    self.static_files.append(StaticFile(name=unit_file.name, data=data))
        # Apply some transformations to the OLX:
        self.transform_olx(olx_node)
        # Add  <xblock-include /> tags for each child (XBlock XML export
        # normally puts children inline as e.g. <html> tags, but we want
        # references to them only.)
        if block.has_children:
            for child_id in block.children:
                # In modulestore, the "definition key" is a MongoDB ObjectID
                # kept in split's definitions table, which theoretically allows
                # the same block to be used in many places (each with a unique
                # usage key). However, that functionality is not exposed in
                # Studio (other than via content libraries). So when we import
                # into Blockstore, we assume that each usage is unique, don't
                # generate a usage key, and create a new "definition key" from
                # the original usage key.
                # So modulestore usage key
                #     block-v1:A+B+C+type@html+block@introduction
                # will become Blockstore definition key
                #     html+introduction
                #
                # If we needed the real definition key, we could get it via
                #     child = block.runtime.get_block(child_id)
                #     child_def_id = six.text_type(child.scope_ids.def_id)
                # and then use
                #     <xblock-include definition={child_def_id} usage={child_id.block_id} />
                def_id = blockstore_def_key_from_modulestore_usage_key(child_id)
                olx_node.append(olx_node.makeelement("xblock-include", {"definition": def_id}))
        # Store the resulting XML as a string:
        self.olx_str = etree_tostring(olx_node, encoding="utf-8", pretty_print=True)
        # And add a comment:
        self.olx_str += (
            '<!-- Imported from {} using openedx-blockstore-relay -->\n'.format(six.text_type(self.orig_block_key))
        ).encode('utf-8')
        # Search the OLX for references to files stored in the course's
        # "Files & Uploads" (contentstore):
        course_key = self.orig_block_key.course_key
        for asset in compat.collect_assets_from_text(self.olx_str, course_key):
            # TODO: need to rewrite the URLs/paths in the olx_str to the new format/location
            self.add_static_asset(asset['content'])
        # Special case: for HTML blocks, the HTML we need to scan is in a separate .html file,
        # not in the OLX string. But we can access it at 'block.data':
        if self.orig_block_key.block_type == 'html':
            for asset in compat.collect_assets_from_text(block.data, course_key):
                self.add_static_asset(asset['content'])

    def add_static_asset(self, asset):
        """
        Add the given contentstore StaticContent file to the's list of static
        files that this block uses.
        """
        # note: asset.name is a human-friendly name, not necessarily the file name.
        filename = asset.location.path
        if filename not in [sf.name for sf in self.static_files]:
            self.static_files.append(StaticFile(name=filename, data=asset.data))

    def transform_olx(self, olx_node):
        """
        Apply transformations to the given OLX etree Node.
        """
        # Remove 'url_name' - we store the definition key in the folder name
        # that holds the OLX and the usage key elsewhere, so specifying it
        # within the OLX file is redundant and can lead to issues if the file is
        # copied and pasted elsewhere in the bundle with a new definition key.
        olx_node.attrib.pop('url_name', None)
        # Convert <vertical> to the new <unit> tag/block
        if olx_node.tag == 'vertical':
            olx_node.tag = 'unit'
            for key in olx_node.attrib.keys():
                if key not in ('display_name', 'url_name'):
                    log.warn('<vertical> tag attribute "%s" will be ignored after conversion to <unit>', key)
