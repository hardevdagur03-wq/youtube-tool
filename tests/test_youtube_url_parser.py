"""Tests for Phase 2 — YouTube URL Parser.

Target: 95%+ coverage of ``services.youtube_url_parser.YouTubeURLParser``
and ``utils.url_helpers``.
"""

import pytest

from exceptions import YouTubeURLError
from services.youtube_url_parser import YouTubeURLParser
from utils.url_helpers import (
    clean_url_input,
    extract_video_id_from_query,
    has_valid_scheme,
    is_supported_path,
    is_youtube_domain,
    normalize_url,
    validate_video_id,
)

VALID_VIDEO_ID = "dQw4w9WgXcQ"
VALID_VIDEO_ID_2 = "5NV6Rdv1a3I"
VALID_VIDEO_ID_SHORTS = "abc123DEF_-"

parser = YouTubeURLParser()


class TestIsYoutubeDomain:
    def test_standard_youtube(self):
        assert is_youtube_domain("www.youtube.com") is True

    def test_short_domain(self):
        assert is_youtube_domain("youtu.be") is True

    def test_mobile_domain(self):
        assert is_youtube_domain("m.youtube.com") is True

    def test_music_domain(self):
        assert is_youtube_domain("music.youtube.com") is True

    def test_no_www(self):
        assert is_youtube_domain("youtube.com") is True

    def test_nocookie_domain(self):
        assert is_youtube_domain("www.youtube-nocookie.com") is True

    def test_nocookie_without_www(self):
        assert is_youtube_domain("youtube-nocookie.com") is True

    def test_non_youtube(self):
        assert is_youtube_domain("google.com") is False
        assert is_youtube_domain("facebook.com") is False
        assert is_youtube_domain("vimeo.com") is False
        assert is_youtube_domain("localhost") is False
        assert is_youtube_domain("") is False

    def test_case_insensitive(self):
        assert is_youtube_domain("WWW.YOUTUBE.COM") is True
        assert is_youtube_domain("YOUTUBE.COM") is True
        assert is_youtube_domain("YOUTU.BE") is True
        assert is_youtube_domain("M.YOUTUBE.COM") is True
        assert is_youtube_domain("MUSIC.YOUTUBE.COM") is True
        assert is_youtube_domain("WWW.YOUTUBE-NOCOOKIE.COM") is True


class TestIsSupportedPath:
    def test_watch_path(self):
        assert is_supported_path("/watch") is True

    def test_shorts_path(self):
        assert is_supported_path("/shorts/abc123") is True

    def test_live_path(self):
        assert is_supported_path("/live/abc123") is True

    def test_embed_path(self):
        assert is_supported_path("/embed/abc123") is True

    def test_channel_path_unsupported(self):
        assert is_supported_path("/channel/UC_xxx") is False

    def test_user_path_unsupported(self):
        assert is_supported_path("/user/username") is False

    def test_handle_path_unsupported(self):
        assert is_supported_path("/@handle") is False

    def test_c_path_unsupported(self):
        assert is_supported_path("/c/channelname") is False

    def test_playlist_path_unsupported(self):
        assert is_supported_path("/playlist") is False

    def test_feed_path_unsupported(self):
        assert is_supported_path("/feed/trending") is False

    def test_results_path_unsupported(self):
        assert is_supported_path("/results") is False

    def test_hashtag_path_unsupported(self):
        assert is_supported_path("/hashtag/gaming") is False

    def test_account_path_unsupported(self):
        assert is_supported_path("/account") is False

    def test_root_path_supported(self):
        assert is_supported_path("/") is True

    def test_case_insensitive(self):
        assert is_supported_path("/CHANNEL/UC_xxx") is False
        assert is_supported_path("/PLAYLIST?list=PL_xxx") is False


class TestExtractVideoIdFromQuery:
    def test_simple_v_query(self):
        assert extract_video_id_from_query(f"v={VALID_VIDEO_ID}") == VALID_VIDEO_ID

    def test_v_query_with_extra_params(self):
        assert (
            extract_video_id_from_query(f"v={VALID_VIDEO_ID}&t=120&feature=share")
            == VALID_VIDEO_ID
        )

    def test_v_query_with_list(self):
        assert (
            extract_video_id_from_query(f"v={VALID_VIDEO_ID}&list=PL_xxx&si=abc123")
            == VALID_VIDEO_ID
        )

    def test_v_query_with_pp(self):
        assert (
            extract_video_id_from_query(f"v={VALID_VIDEO_ID}&pp=ygUJcmljaCB3b29k")
            == VALID_VIDEO_ID
        )

    def test_no_v_param(self):
        assert extract_video_id_from_query("t=120&feature=share") is None

    def test_no_v_param_only_si(self):
        assert extract_video_id_from_query("si=I1Fpe6XsxkGybZCF") is None

    def test_empty_query(self):
        assert extract_video_id_from_query("") is None

    def test_v_param_empty(self):
        assert extract_video_id_from_query("v=") is None

    def test_multiple_v_params_takes_first(self):
        assert (
            extract_video_id_from_query(f"v={VALID_VIDEO_ID}&v={VALID_VIDEO_ID_2}")
            == VALID_VIDEO_ID
        )


class TestValidateVideoId:
    def test_valid_11_chars(self):
        assert validate_video_id(VALID_VIDEO_ID) == VALID_VIDEO_ID

    def test_valid_with_hyphen_and_underscore(self):
        assert validate_video_id(VALID_VIDEO_ID_SHORTS) == VALID_VIDEO_ID_SHORTS

    def test_too_short(self):
        with pytest.raises(YouTubeURLError, match="Invalid video ID format"):
            validate_video_id("abc")

    def test_too_long(self):
        with pytest.raises(YouTubeURLError, match="Invalid video ID format"):
            validate_video_id("a" * 12)

    def test_special_characters(self):
        with pytest.raises(YouTubeURLError, match="Invalid video ID format"):
            validate_video_id("abc def!@#")

    def test_empty_string(self):
        with pytest.raises(YouTubeURLError, match="Video ID is missing or empty"):
            validate_video_id("")

    def test_whitespace(self):
        with pytest.raises(YouTubeURLError, match="Video ID is missing or empty"):
            validate_video_id("   ")


class TestNormalizeUrl:
    def test_normalizes_correctly(self):
        result = normalize_url(VALID_VIDEO_ID)
        assert result == f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}"

    def test_normalizes_other_id(self):
        result = normalize_url(VALID_VIDEO_ID_2)
        assert result == f"https://www.youtube.com/watch?v={VALID_VIDEO_ID_2}"


class TestCleanUrlInput:
    def test_removes_whitespace(self):
        result = clean_url_input(f"  https://youtu.be/{VALID_VIDEO_ID}  ")
        assert result == f"https://youtu.be/{VALID_VIDEO_ID}"

    def test_empty_raises(self):
        with pytest.raises(YouTubeURLError, match="Empty or invalid"):
            clean_url_input("")

    def test_whitespace_only_raises(self):
        with pytest.raises(YouTubeURLError, match="Empty or invalid"):
            clean_url_input("   ")

    def test_none_raises(self):
        with pytest.raises(YouTubeURLError, match="Empty or invalid"):
            clean_url_input(None)

    def test_non_string_raises(self):
        with pytest.raises(YouTubeURLError, match="Empty or invalid"):
            clean_url_input(123)


class TestHasValidScheme:
    def test_https(self):
        assert has_valid_scheme("https://youtube.com/watch?v=abc") is True

    def test_http(self):
        assert has_valid_scheme("http://youtube.com/watch?v=abc") is True

    def test_missing_scheme(self):
        assert has_valid_scheme("youtube.com/watch?v=abc") is False

    def test_ftp_rejected(self):
        assert has_valid_scheme("ftp://youtube.com/watch?v=abc") is False

    def test_empty(self):
        assert has_valid_scheme("") is False


class TestYouTubeURLParserValidFormats:
    """All supported YouTube URL formats must return valid=True."""

    def test_standard_watch_url(self):
        url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.normalized_url == f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}"
        assert result.url_type == "watch"
        assert result.error is None

    def test_short_youtu_be_url(self):
        url = f"https://youtu.be/{VALID_VIDEO_ID}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.url_type == "youtu.be"

    def test_shorts_url(self):
        url = f"https://www.youtube.com/shorts/{VALID_VIDEO_ID_SHORTS}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID_SHORTS
        assert result.url_type == "shorts"

    def test_live_url(self):
        url = f"https://www.youtube.com/live/{VALID_VIDEO_ID}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.url_type == "live"

    def test_embed_url(self):
        url = f"https://www.youtube.com/embed/{VALID_VIDEO_ID}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.url_type == "embed"

    def test_mobile_url(self):
        url = f"https://m.youtube.com/watch?v={VALID_VIDEO_ID}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.url_type == "watch"

    def test_music_url(self):
        url = f"https://music.youtube.com/watch?v={VALID_VIDEO_ID}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.url_type == "watch"

    def test_nocookie_embed_url(self):
        url = f"https://www.youtube-nocookie.com/embed/{VALID_VIDEO_ID}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.url_type == "embed"


class TestYouTubeURLParserWithExtraParams:
    """URLs with extra query parameters must still parse correctly."""

    def test_with_timestamp(self):
        url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}&t=120"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_with_si_param(self):
        url = f"https://youtu.be/{VALID_VIDEO_ID}?si=I1Fpe6XsxkGybZCF"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_with_pp_param(self):
        url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}&pp=ygUJcmljaCB3b29k"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_with_feature_share(self):
        url = f"https://youtu.be/{VALID_VIDEO_ID}?feature=share"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_with_list_param(self):
        url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}&list=PL_abc123&si=xyz"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_with_multiple_params(self):
        url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}&t=60&feature=shared&list=PL_xyz&index=2"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_shorts_with_params(self):
        url = f"https://www.youtube.com/shorts/{VALID_VIDEO_ID_SHORTS}?feature=share"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID_SHORTS

    def test_live_with_params(self):
        url = f"https://www.youtube.com/live/{VALID_VIDEO_ID}?t=300"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_embed_with_params(self):
        url = f"https://www.youtube.com/embed/{VALID_VIDEO_ID}?autoplay=1&mute=1"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_si_and_pp_together(self):
        url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}&si=abc123&pp=iQMF"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID


class TestYouTubeURLParserNoScheme:
    """URLs without a scheme should still be parsed."""

    def test_without_scheme(self):
        result = parser.parse(f"www.youtube.com/watch?v={VALID_VIDEO_ID}")
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_youtu_be_without_scheme(self):
        result = parser.parse(f"youtu.be/{VALID_VIDEO_ID}")
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID


class TestYouTubeURLParserInvalidInputs:
    def test_empty_string(self):
        result = parser.parse("")
        assert result.valid is False
        assert result.error is not None

    def test_whitespace_only(self):
        result = parser.parse("   ")
        assert result.valid is False
        assert result.error is not None

    def test_random_text(self):
        result = parser.parse("hello world this is not a url")
        assert result.valid is False
        assert result.error is not None

    def test_google_search_url(self):
        result = parser.parse("https://www.google.com/search?q=youtube")
        assert result.valid is False
        assert "domain" in (result.error or "").lower()

    def test_facebook_url(self):
        result = parser.parse("https://www.facebook.com/watch?v=abc123")
        assert result.valid is False
        assert "domain" in (result.error or "").lower()

    def test_instagram_url(self):
        result = parser.parse("https://www.instagram.com/p/abc123/")
        assert result.valid is False

    def test_tiktok_url(self):
        result = parser.parse("https://www.tiktok.com/@user/video/123")
        assert result.valid is False

    def test_twitter_url(self):
        result = parser.parse("https://twitter.com/user/status/123")
        assert result.valid is False

    def test_vimeo_url(self):
        result = parser.parse("https://vimeo.com/12345678")
        assert result.valid is False

    def test_local_file(self):
        result = parser.parse("file:///C:/video.mp4")
        assert result.valid is False


class TestYouTubeURLParserUnsupportedResources:
    def test_channel_url(self):
        result = parser.parse("https://www.youtube.com/channel/UC_abc123")
        assert result.valid is False
        assert "channel" in (result.error or "").lower()

    def test_channel_handle_url(self):
        result = parser.parse("https://www.youtube.com/@physicsgalaxyworld")
        assert result.valid is False
        assert "channel" in (result.error or "").lower()

    def test_user_url(self):
        result = parser.parse("https://www.youtube.com/user/username")
        assert result.valid is False
        assert "channel" in (result.error or "").lower()

    def test_custom_url(self):
        result = parser.parse("https://www.youtube.com/c/customname")
        assert result.valid is False
        assert "channel" in (result.error or "").lower()

    def test_playlist_url(self):
        result = parser.parse("https://www.youtube.com/playlist?list=PL_abc123")
        assert result.valid is False
        assert "playlist" in (result.error or "").lower()

    def test_feed_trending(self):
        result = parser.parse("https://www.youtube.com/feed/trending")
        assert result.valid is False

    def test_results_search(self):
        result = parser.parse("https://www.youtube.com/results?search_query=test")
        assert result.valid is False

    def test_account(self):
        result = parser.parse("https://www.youtube.com/account")
        assert result.valid is False

    def test_hashtag(self):
        result = parser.parse("https://www.youtube.com/hashtag/gaming")
        assert result.valid is False

    def test_studio_url(self):
        result = parser.parse("https://studio.youtube.com/video/abc123/edit")
        assert result.valid is False
        assert "domain" in (result.error or "").lower()


class TestYouTubeURLParserMalformed:
    def test_invalid_video_id_length(self):
        url = "https://www.youtube.com/watch?v=tooshort"
        result = parser.parse(url)
        assert result.valid is False

    def test_invalid_video_id_chars(self):
        url = "https://www.youtube.com/watch?v=!!!invalid!!!"
        result = parser.parse(url)
        assert result.valid is False

    def test_missing_video_id(self):
        result = parser.parse("https://www.youtube.com/watch")
        assert result.valid is False
        assert "video id not found" in (result.error or "").lower()

    def test_watch_without_v_param(self):
        result = parser.parse("https://www.youtube.com/watch?feature=share")
        assert result.valid is False

    def test_short_url_missing_id(self):
        result = parser.parse("https://youtu.be/")
        assert result.valid is False

    def test_short_url_only_domain(self):
        result = parser.parse("https://youtu.be")
        assert result.valid is False

    def test_multiple_v_params_takes_first(self):
        result = parser.parse("https://www.youtube.com/watch?v=dQw4w9WgXcQ&v=5NV6Rdv1a3I&v=abc123DEF_-")
        assert result.valid is True
        assert result.video_id == "dQw4w9WgXcQ"

    def test_unsupported_protocol(self):
        result = parser.parse("ftp://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result.valid is False


class TestYouTubeURLParserEdgeCases:
    def test_url_with_trailing_slash_in_path(self):
        url = f"https://www.youtube.com/watch/?v={VALID_VIDEO_ID}"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID

    def test_url_with_ampersand_encoding(self):
        url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}&amp;t=120"
        result = parser.parse(url)
        assert result.valid is True

    def test_original_url_is_preserved(self):
        url = f"https://youtu.be/{VALID_VIDEO_ID}?feature=share"
        result = parser.parse(url)
        assert result.original_url == url

    def test_normalized_url_always_watch(self):
        result = parser.parse(f"https://youtu.be/{VALID_VIDEO_ID}")
        assert result.normalized_url == f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}"

        result = parser.parse(f"https://www.youtube.com/shorts/{VALID_VIDEO_ID}")
        assert result.normalized_url == f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}"

    def test_video_id_with_hyphen(self):
        video_id = "abc-defghij"
        result = parser.parse(f"https://www.youtube.com/watch?v={video_id}")
        assert result.valid is True
        assert result.video_id == video_id

    def test_video_id_with_underscore(self):
        video_id = "abc_defghij"
        result = parser.parse(f"https://www.youtube.com/watch?v={video_id}")
        assert result.valid is True
        assert result.video_id == video_id

    def test_mixed_case_video_id(self):
        video_id = "AbCdEfGhIjK"
        result = parser.parse(f"https://www.youtube.com/watch?v={video_id}")
        assert result.valid is True
        assert result.video_id == video_id

    def test_youtube_nocookie_with_params(self):
        url = f"https://www.youtube-nocookie.com/embed/{VALID_VIDEO_ID}?autoplay=1&si=abc"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.url_type == "embed"

    def test_youtu_be_with_si(self):
        url = f"https://youtu.be/{VALID_VIDEO_ID}?si=I1Fpe6XsxkGybZCF"
        result = parser.parse(url)
        assert result.valid is True
        assert result.video_id == VALID_VIDEO_ID
        assert result.url_type == "youtu.be"


class TestYouTubeURLParserReusability:
    """Parser is stateless — multiple calls should work."""

    def test_multiple_calls_same_instance(self):
        results = [
            parser.parse("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            parser.parse("https://youtu.be/5NV6Rdv1a3I"),
            parser.parse("https://www.youtube.com/shorts/abc123DEF_-"),
            parser.parse("https://invalid.com/watch?v=test"),
        ]
        assert results[0].valid is True
        assert results[0].video_id == "dQw4w9WgXcQ"
        assert results[1].valid is True
        assert results[1].video_id == "5NV6Rdv1a3I"
        assert results[2].valid is True
        assert results[2].video_id == "abc123DEF_-"
        assert results[3].valid is False

    def test_different_url_types_return_correct_types(self):
        type_map = {
            f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}": "watch",
            f"https://youtu.be/{VALID_VIDEO_ID}": "youtu.be",
            f"https://www.youtube.com/shorts/{VALID_VIDEO_ID}": "shorts",
            f"https://www.youtube.com/live/{VALID_VIDEO_ID}": "live",
            f"https://www.youtube.com/embed/{VALID_VIDEO_ID}": "embed",
        }
        for url, expected_type in type_map.items():
            result = parser.parse(url)
            assert result.valid is True, f"URL failed: {url}"
            assert result.url_type == expected_type, f"Expected {expected_type}, got {result.url_type} for {url}"


class TestYouTubeURLParserCaseInsensitive:
    def test_uppercase_domain_and_path(self):
        result = parser.parse("WWW.YOUTUBE.COM/WATCH?V=DQW4W9WGXCQ")
        assert result.valid is True
        assert result.video_id == "DQW4W9WGXCQ"
        assert result.url_type == "watch"

    def test_uppercase_shorts(self):
        result = parser.parse("HTTPS://WWW.YOUTUBE.COM/SHORTS/DQW4W9WGXCQ")
        assert result.valid is True
        assert result.video_id == "DQW4W9WGXCQ"

    def test_uppercase_youtu_be(self):
        result = parser.parse("YOUTU.BE/DQW4W9WGXCQ")
        assert result.valid is True
        assert result.video_id == "DQW4W9WGXCQ"

    def test_mixed_case_domain(self):
        result = parser.parse("https://WwW.YoUtUbE.cOm/wAtCh?v=dQw4w9WgXcQ")
        assert result.valid is True
        assert result.video_id == "dQw4w9WgXcQ"

    def test_uppercase_embed(self):
        result = parser.parse("HTTPS://WWW.YOUTUBE.COM/EMBED/DQW4W9WGXCQ")
        assert result.valid is True
        assert result.video_id == "DQW4W9WGXCQ"

    def test_uppercase_live(self):
        result = parser.parse("HTTPS://WWW.YOUTUBE.COM/LIVE/DQW4W9WGXCQ")
        assert result.valid is True
        assert result.video_id == "DQW4W9WGXCQ"
