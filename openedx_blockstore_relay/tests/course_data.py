# -*- coding: utf-8 -*-
"""
A course containing each of the features whose export functionality we want to test
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import edxval.api as edxval_api
from django.core.files.base import ContentFile

from xmodule.contentstore.content import StaticContent
from xmodule.contentstore.django import contentstore
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.factories import SampleCourseFactory
from xmodule.modulestore.tests.sample_courses import BlockInfo

TEST_COURSE = [
    BlockInfo(
        'section1', 'chapter', {}, [
            BlockInfo(
                'subsection1_1', 'sequential', {"display_name": "Subsection 1.1"}, [
                    BlockInfo(
                        'unit1_1_1', 'vertical', {}, [
                            BlockInfo('html_a', 'html', {
                                "data": ("<p>There is a <strong>CAPA Problem</strong> below.</p>"),
                                "display_name": "Problem Introduction",
                            }, []),
                            BlockInfo('problem_a', 'problem', {
                                "data": (
                                    "<problem><multiplechoiceresponse>"
                                    "    <choicegroup type='MultipleChoice'>"
                                    "        <choice correct='false'>wrong</choice>"
                                    "        <choice correct='true'>right</choice>"
                                    "    </choicegroup>"
                                    "</multiplechoiceresponse></problem>"
                                )
                            }, []),
                            BlockInfo('problem_b', 'problem', {
                                "display_name": "Pointing on a Picture",
                                "max_attempts": None,
                                "data": (
                                    "<problem>"
                                    "<p>Answer this question by clicking on the image below.</p>"
                                    "<imageresponse>"
                                    "    <imageinput src='/static/edx.svg' width='640' height='400' "
                                    "        rectangle='(385,98)-(600,337)'/>"
                                    "</imageresponse>"
                                    "<solution><div class='detailed-solution'><p>Explanation here.</p></div></solution>"
                                    "</problem>"
                                )
                            }, []),
                        ]
                    ),
                    BlockInfo(
                        'unit1_1_2', 'vertical', {"display_name": "Unit 1.1.2"}, [
                            BlockInfo('html_b', 'html', {
                                "data": (
                                    '<p>'
                                    # 'Blockstore video export is 🔥. '
                                    # ^ The HTML XModule strips out emoji (why?), so we can't use this.
                                    'Activate the ωμέγα 13! '
                                    '<a href="/static/sample_handout.txt">Instructions.</a>'
                                    '</p>'
                                ),
                                "display_name": "Unicode and URL test",
                            }, []),
                            BlockInfo('video_b', 'video', {
                                "transcripts": {"en": "50ce37bf-594a-425c-9892-6407a5083eb3-en.srt"},
                                "display_name": "YouTube Video",
                                "edx_video_id": "50ce37bf-594a-425c-9892-6407a5083eb3",
                                "youtube_id_1_0": "3_yD_cEKoCk",
                                "data": (
                                    '<video>'
                                    '  <video_asset client_video_id="video_b_123" duration="0.0" image="">'
                                    '    <transcripts>'
                                    '      <transcript file_format="srt" language_code="en" provider="Custom"/>'
                                    '    </transcripts>'
                                    '  </video_asset>'
                                    '  <transcript language="en" src="50ce37bf-594a-425c-9892-6407a5083eb3-en.srt"/>'
                                    '</video>'
                                ),
                            }, []),
                            # We also need to test with a block that doesn't use _any_ XModule mixins:
                            BlockInfo('dnd', 'drag-and-drop-v2', {
                                "display_name": "A Drag and Drop Block (Pure XBlock)",
                            }, []),
                        ]
                    ),
                ]
            ),
        ]
    ),
]

# Additional information required for the "video_b" video to work:
VIDEO_B_EDX_VIDEO_ID = '50ce37bf-594a-425c-9892-6407a5083eb3'
VIDEO_B_VAL_DATA = {
    'edx_video_id': VIDEO_B_EDX_VIDEO_ID,
    'status': edxval_api.EXTERNAL_VIDEO_STATUS,
    'client_video_id': 'video_b_123',
    'duration': 0,
    'encoded_videos': [],
    'courses': [],
}

VIDEO_B_SRT_TRANSCRIPT_CONTENT = """0
00:00:00,260 --> 00:00:01,510
ANANT AGARWAL: Welcome to edX.

""".encode('utf8')

VIDEO_B_SRT_TRANSCRIPT_DATA = {
    "video_id": VIDEO_B_EDX_VIDEO_ID,
    "language_code": 'en',
    "file_format": edxval_api.TranscriptFormat.SRT,
    "content": ContentFile(VIDEO_B_SRT_TRANSCRIPT_CONTENT),
}


class TestCourseMixin(object):
    """
    Mixin that creates a full modulestore test course that can be used.

    Must be mixed into a test case that inherits from ModuleStoreTestCase.
    """
    COLLECTION_UUID = 'd3e311a8-b3a8-439d-a111-cc6cb99790e8'
    BUNDLE_UUID = '93fc9c6e-4249-4d57-a63c-b08be9f4fe02'

    def setUp(self):
        super(TestCourseMixin, self).setUp()

        with modulestore().default_store(ModuleStoreEnum.Type.split):
            self.course = SampleCourseFactory.create(block_info_tree=TEST_COURSE)
        # And upload the course static asssets:
        asset_key = StaticContent.compute_location(self.course.id, 'sample_handout.txt')
        content = StaticContent(asset_key, "Fake asset", "application/text", "test".encode('utf8'))
        contentstore().save(content)

        asset_key = StaticContent.compute_location(self.course.id, 'edx.svg')
        content = StaticContent(asset_key, "Fake image", "image/svg+xml", """
            <svg viewBox="0 0 403 403" version="1.1"
                xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
            >
                <title>edX</title>
                <desc>
                    the edX logo is comprised of a red letter e, grey d, and blue uppercase X, all slightly overlapping
                    each other.  The d is slightly transparent.
                </desc>
                <g transform="translate(0,100)">
                    <path id="e-path" stroke-width="1" stroke="none" fill="rgb(185, 0, 88)" fill-rule="evenodd"
                        d="M32.1,127 H141.9 A71,71.5 0 1,0 137.3,143 H103 A42,42 0 0,1 32.1,127 M32.1,102.5 H112 A42,42
                        0 0,0 32.1,102.5"/>
                    <path id="x-path" stroke-width="1" stroke="none" fill="rgb(0, 162, 228)" fill-rule="evenodd"
                        d="M228,1 H302 V31 H286 L315,67 L344,31 H328 V1 H401.5 V31 H385 L335.2,92.4 L387.5,156.8 H401.5
                        V187 H328 V156.8 H346.5 L315,117.4 L283,156.8 H302.0 V187 H228.5 V156.8 H243 L294.3,92.4
                        L244,30.5 H228 V1"/>
                    <path id="d-path" stroke-width="1" stroke="none" fill="rgb(55, 55, 60)" fill-rule="evenodd"
                        opacity="0.55" d="M198.5,1 L248,1 V156.5 H269.8 V187 H217.5 V174 A71.7,71.7 0 1,1 218,55.5
                        V30.5 H198.5 V1 M218,114 A41,41.5 0 1,1 136.1,114 A40.5,40.5 0 1,1 218,114"/>
                </g>
            </svg>
        """.strip().encode('utf8'))
        contentstore().save(content)
        # And the video data + transcript must also be stored in edx-val for the video export to work:
        edxval_api.create_video(VIDEO_B_VAL_DATA)
        edxval_api.create_video_transcript(**VIDEO_B_SRT_TRANSCRIPT_DATA)
