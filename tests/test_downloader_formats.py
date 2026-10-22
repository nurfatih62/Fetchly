"""Test helper format video tanpa menghubungi YouTube atau TikTok."""

from __future__ import annotations

import unittest

from app.services.downloader import _available_formats


class AvailableFormatsTests(unittest.TestCase):
    def test_only_exact_standard_heights_are_returned(self) -> None:
        info = {
            "formats": [
                {"height": 1080, "vcodec": "avc1"},
                {"height": 720, "vcodec": "avc1"},
                {"height": 576, "vcodec": "avc1"},
                {"height": 360, "vcodec": "vp9"},
            ]
        }
        self.assertEqual(
            _available_formats(info),
            [
                {"quality": "1080p", "height": 1080},
                {"quality": "720p", "height": 720},
                {"quality": "360p", "height": 360},
            ],
        )

    def test_audio_only_and_missing_heights_are_ignored(self) -> None:
        info = {
            "formats": [
                {"height": 720, "vcodec": "none"},
                {"height": None, "vcodec": "avc1"},
                {"vcodec": "avc1"},
                {"height": 240, "vcodec": "avc1"},
            ]
        }
        self.assertEqual(_available_formats(info), [])

    def test_missing_formats_returns_empty_list(self) -> None:
        self.assertEqual(_available_formats({}), [])


if __name__ == "__main__":
    unittest.main()
