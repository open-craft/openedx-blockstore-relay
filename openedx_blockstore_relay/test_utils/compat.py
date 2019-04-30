"""
Test compatibility layer that reduces dependence on edx-platform.
"""

from __future__ import absolute_import, division, print_function, unicode_literals


class StubCompat(object):
    """
    Stub version of 'compat' library for use in tests
    """
    # pylint: disable=unused-argument

    def __init__(self, blocks, assets=None, video_assets=None):
        self.blocks = blocks
        self.assets = assets
        self.video_assets = video_assets

    def get_block(self, usage_key):
        return self.blocks[usage_key]

    def collect_assets_from_text(self, text, course_id):
        if self.assets:
            return self.assets
        return []

    def collect_assets_from_video_block(self, block):
        if self.video_assets:
            return self.video_assets
        return []


class StaticContent(object):

    def __init__(self, data):
        self.data = data
        self.content_type = 'content_type'
