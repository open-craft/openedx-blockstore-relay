# -*- coding: utf-8 -*-
"""
A course containing each of the features whose export functionality we want to test
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from django.core.files.base import ContentFile
from edxval.api import EXTERNAL_VIDEO_STATUS, TranscriptFormat
from xmodule.modulestore.tests.sample_courses import BlockInfo

TEST_COURSE = [
    BlockInfo(
        'section1', 'chapter', {}, [
            BlockInfo(
                'subsection1_1', 'sequential', {}, [
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
                        ]
                    ),
                    BlockInfo(
                        'unit1_1_2', 'vertical', {}, [
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
                                    '  <video_asset client_video_id="external video" duration="0.0" image="">'
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
    'status': EXTERNAL_VIDEO_STATUS,
    'client_video_id': 'A Video',
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
    "file_format": TranscriptFormat.SRT,
    "content": ContentFile(VIDEO_B_SRT_TRANSCRIPT_CONTENT),
}
