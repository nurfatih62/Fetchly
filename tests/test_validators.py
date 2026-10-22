"""Unit test untuk validasi tautan YouTube dan TikTok."""

from __future__ import annotations

import unittest

from app.utils.validators import URLValidationError, validate_video_url

YOUTUBE_ID = "dQw4w9WgXcQ"


class ValidURLTests(unittest.TestCase):
    def test_youtube_watch(self) -> None:
        result = validate_video_url(
            f"https://www.youtube.com/watch?v={YOUTUBE_ID}"
        )
        self.assertEqual(result.platform, "youtube")
        self.assertEqual(result.video_id, YOUTUBE_ID)
        self.assertEqual(
            result.url, f"https://www.youtube.com/watch?v={YOUTUBE_ID}"
        )

    def test_youtube_without_www(self) -> None:
        result = validate_video_url(
            f"https://youtube.com/watch?v={YOUTUBE_ID}"
        )
        self.assertEqual(result.platform, "youtube")
        self.assertEqual(
            result.url, f"https://www.youtube.com/watch?v={YOUTUBE_ID}"
        )

    def test_youtube_mobile(self) -> None:
        result = validate_video_url(
            f"https://m.youtube.com/watch?v={YOUTUBE_ID}"
        )
        self.assertEqual(result.platform, "youtube")

    def test_youtu_be_short_link(self) -> None:
        result = validate_video_url(f"https://youtu.be/{YOUTUBE_ID}")
        self.assertEqual(result.platform, "youtube")
        self.assertEqual(
            result.url, f"https://www.youtube.com/watch?v={YOUTUBE_ID}"
        )

    def test_youtube_shorts(self) -> None:
        result = validate_video_url(
            f"https://www.youtube.com/shorts/{YOUTUBE_ID}"
        )
        self.assertEqual(result.video_id, YOUTUBE_ID)

    def test_youtube_live_and_embed(self) -> None:
        for path in ("live", "embed"):
            with self.subTest(path=path):
                result = validate_video_url(
                    f"https://www.youtube.com/{path}/{YOUTUBE_ID}"
                )
                self.assertEqual(result.video_id, YOUTUBE_ID)

    def test_http_is_upgraded_and_tracking_is_removed(self) -> None:
        result = validate_video_url(
            f"http://www.youtube.com/watch?v={YOUTUBE_ID}"
            "&list=PL123&index=4&t=30#bagian"
        )
        self.assertEqual(
            result.url, f"https://www.youtube.com/watch?v={YOUTUBE_ID}"
        )

    def test_uppercase_host_and_surrounding_spaces(self) -> None:
        result = validate_video_url(f"  HTTPS://WWW.YOUTUBE.COM/watch?v={YOUTUBE_ID}  ")
        self.assertEqual(result.url, f"https://www.youtube.com/watch?v={YOUTUBE_ID}")

    def test_youtube_extra_query_parameters(self) -> None:
        result = validate_video_url(
            f"https://www.youtube.com/watch?app=desktop&v={YOUTUBE_ID}&feature=share"
        )
        self.assertEqual(result.video_id, YOUTUBE_ID)

    def test_tiktok_video(self) -> None:
        result = validate_video_url(
            "https://www.tiktok.com/@Nama.Kreator/video/7412345678901234567?lang=id"
        )
        self.assertEqual(result.platform, "tiktok")
        self.assertEqual(result.video_id, "7412345678901234567")
        self.assertEqual(
            result.url,
            "https://www.tiktok.com/@nama.kreator/video/7412345678901234567",
        )

    def test_tiktok_short_links(self) -> None:
        for host in ("vm.tiktok.com", "vt.tiktok.com"):
            with self.subTest(host=host):
                result = validate_video_url(f"https://{host}/ZMabc123/?k=1")
                self.assertEqual(result.platform, "tiktok")
                self.assertEqual(result.url, f"https://{host}/ZMabc123")

    def test_maximum_length_is_inclusive(self) -> None:
        prefix = f"https://www.youtube.com/watch?v={YOUTUBE_ID}&x="
        raw = prefix + ("a" * (2048 - len(prefix)))
        self.assertEqual(len(raw), 2048)
        result = validate_video_url(raw)
        self.assertEqual(result.video_id, YOUTUBE_ID)


class InvalidURLTests(unittest.TestCase):
    def assert_invalid(self, raw: object, code: str = "INVALID_URL") -> None:
        with self.assertRaises(URLValidationError) as context:
            validate_video_url(raw)  # type: ignore[arg-type]
        self.assertEqual(context.exception.code, code)

    def test_empty_and_whitespace(self) -> None:
        self.assert_invalid("")
        self.assert_invalid("   ")

    def test_too_long(self) -> None:
        prefix = f"https://www.youtube.com/watch?v={YOUTUBE_ID}&x="
        raw = prefix + ("a" * (2049 - len(prefix)))
        self.assertEqual(len(raw), 2049)
        self.assert_invalid(raw)

    def test_wrong_scheme(self) -> None:
        self.assert_invalid(f"ftp://www.youtube.com/watch?v={YOUTUBE_ID}")
        self.assert_invalid(f"javascript:alert('{YOUTUBE_ID}')")
        self.assert_invalid(f"www.youtube.com/watch?v={YOUTUBE_ID}")

    def test_fake_youtube_domains(self) -> None:
        self.assert_invalid(
            f"https://youtube.com.evil.net/watch?v={YOUTUBE_ID}"
        )
        self.assert_invalid(
            f"https://www.youtube.com.evil.net/watch?v={YOUTUBE_ID}"
        )
        self.assert_invalid(
            f"https://notyoutube.com/watch?v={YOUTUBE_ID}"
        )
        self.assert_invalid(
            f"https://evil.net/watch?v={YOUTUBE_ID}&next=https://youtube.com"
        )

    def test_subdomain_outside_whitelist(self) -> None:
        self.assert_invalid(
            f"https://music.youtube.com/watch?v={YOUTUBE_ID}"
        )
        self.assert_invalid(
            f"https://www.youtube.com./watch?v={YOUTUBE_ID}"
        )

    def test_userinfo_and_ports_are_rejected(self) -> None:
        self.assert_invalid(
            f"https://user@www.youtube.com/watch?v={YOUTUBE_ID}"
        )
        self.assert_invalid(
            f"https://www.youtube.com:8443/watch?v={YOUTUBE_ID}"
        )

    def test_youtube_non_video_paths(self) -> None:
        self.assert_invalid("https://www.youtube.com/")
        self.assert_invalid("https://www.youtube.com/@channel")
        self.assert_invalid("https://www.youtube.com/playlist?list=PL123")
        self.assert_invalid("https://www.youtube.com/watch")
        self.assert_invalid("https://www.youtube.com/watch?v=terlalupendek")
        self.assert_invalid(f"https://www.youtube.com/watch?v={YOUTUBE_ID}&v=abcdefghijk")
        self.assert_invalid(f"https://youtu.be/{YOUTUBE_ID}/tambahan")

    def test_tiktok_invalid_paths(self) -> None:
        self.assert_invalid("https://www.tiktok.com/")
        self.assert_invalid("https://www.tiktok.com/@user")
        self.assert_invalid("https://www.tiktok.com/@user/photo/7412345678901234567")
        self.assert_invalid("https://vm.tiktok.com/")
        self.assert_invalid("https://vt.tiktok.com/dua/bagian")

    def test_urls_with_inner_whitespace(self) -> None:
        self.assert_invalid(
            f"https://www.youtube.com/watch?v={YOUTUBE_ID} yang lain"
        )

    def test_non_string_input(self) -> None:
        self.assert_invalid(None)
        self.assert_invalid(123)

    def test_other_platforms(self) -> None:
        for raw in (
            "https://vimeo.com/123456789",
            "https://www.instagram.com/reel/abc123/",
            "https://x.com/user/status/123456789",
            "https://www.facebook.com/watch/?v=123456789",
            "https://www.dailymotion.com/video/x8abcde",
        ):
            with self.subTest(url=raw):
                self.assert_invalid(raw, "UNSUPPORTED_PLATFORM")


if __name__ == "__main__":
    unittest.main()
