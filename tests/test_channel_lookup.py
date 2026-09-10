"""Tests for Phase 2 – Channel Lookup."""

from unittest.mock import MagicMock, patch

import pytest

from api.channel_service import (
    ChannelNotFoundError,
    ChannelService,
    ChannelServiceError,
)
from services.channel_resolver import (
    ChannelResolver,
    ChannelResolverError,
    InvalidHandleError,
)


class TestChannelResolverValidate:
    """Validation logic – no mocking needed (pure function)."""

    def test_valid_handle_with_at(self):
        assert ChannelResolver.validate_handle("@testchannel") == "@testchannel"

    def test_valid_handle_without_at(self):
        assert ChannelResolver.validate_handle("testchannel") == "@testchannel"

    def test_valid_handle_with_special_chars(self):
        result = ChannelResolver.validate_handle("@my-channel.test_123")
        assert result == "@my-channel.test_123"

    def test_empty_string_raises_error(self):
        with pytest.raises(InvalidHandleError, match="cannot be empty"):
            ChannelResolver.validate_handle("")

    def test_whitespace_only_raises_error(self):
        with pytest.raises(InvalidHandleError, match="cannot be empty"):
            ChannelResolver.validate_handle("   ")

    def test_too_short_handle_raises_error(self):
        with pytest.raises(InvalidHandleError, match="Invalid channel handle"):
            ChannelResolver.validate_handle("@ab")

    def test_invalid_characters_raises_error(self):
        with pytest.raises(InvalidHandleError, match="Invalid channel handle"):
            ChannelResolver.validate_handle("@invalid handle!!!")

    def test_whitespace_in_handle_raises_error(self):
        with pytest.raises(InvalidHandleError, match="Invalid channel handle"):
            ChannelResolver.validate_handle("@my channel")


class TestChannelService:
    """ChannelService API calls with mocked YouTubeClient."""

    @patch("api.channel_service.YouTubeClient")
    def test_resolve_handle_returns_channel_data(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "UC_test123", "snippet": {"title": "Test Channel"}}]
        }

        svc = ChannelService()
        result = svc.resolve_handle("@test")
        assert result["id"] == "UC_test123"

    @patch("api.channel_service.YouTubeClient")
    def test_resolve_handle_empty_items_raises_not_found(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.channels.return_value.list.return_value.execute.return_value = {
            "items": []
        }

        svc = ChannelService()
        with pytest.raises(ChannelNotFoundError, match="No channel found"):
            svc.resolve_handle("@ghost")

    @patch("api.channel_service.YouTubeClient")
    def test_resolve_handle_missing_items_key_raises_not_found(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.channels.return_value.list.return_value.execute.return_value = {}

        svc = ChannelService()
        with pytest.raises(ChannelNotFoundError, match="No channel found"):
            svc.resolve_handle("@ghost")

    @patch("api.channel_service.YouTubeClient")
    def test_resolve_handle_strips_at_prefix(self, mock_client_cls):
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.get_service.return_value = mock_service
        mock_client_cls.return_value = mock_client

        mock_service.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "UC_test"}]
        }

        svc = ChannelService()
        svc.resolve_handle("@test")
        mock_service.channels.return_value.list.assert_called_once_with(
            part="id,snippet", forHandle="test"
        )


class TestChannelResolverResolve:
    """ChannelResolver.resolve orchestration with mocked ChannelService."""

    def test_resolve_returns_channel_id_and_title(self):
        mock_svc = MagicMock(spec=ChannelService)
        mock_svc.resolve_handle.return_value = {
            "id": "UC_test123",
            "snippet": {"title": "Test Channel"},
        }

        resolver = ChannelResolver(channel_service=mock_svc)
        result = resolver.resolve("@testchannel")

        assert result == {
            "channel_id": "UC_test123",
            "title": "Test Channel",
            "handle": "@testchannel",
        }

    def test_handle_without_at_is_normalized(self):
        mock_svc = MagicMock(spec=ChannelService)
        mock_svc.resolve_handle.return_value = {
            "id": "UC_test456",
            "snippet": {"title": "Another Channel"},
        }

        resolver = ChannelResolver(channel_service=mock_svc)
        result = resolver.resolve("testchannel")
        assert result["handle"] == "@testchannel"

    def test_resolve_trims_and_normalizes_handle(self):
        mock_svc = MagicMock(spec=ChannelService)
        mock_svc.resolve_handle.return_value = {
            "id": "UC_test",
            "snippet": {"title": "T"},
        }

        resolver = ChannelResolver(channel_service=mock_svc)
        resolver.resolve("  @testchannel  ")
        mock_svc.resolve_handle.assert_called_once_with("@testchannel")

    def test_nonexistent_handle_raises_resolver_error(self):
        mock_svc = MagicMock(spec=ChannelService)
        mock_svc.resolve_handle.side_effect = ChannelNotFoundError(
            "No channel found for handle: @nonexistent"
        )

        resolver = ChannelResolver(channel_service=mock_svc)
        with pytest.raises(ChannelResolverError, match="No channel found"):
            resolver.resolve("@nonexistent")

    def test_quota_exceeded_raises_resolver_error(self):
        mock_svc = MagicMock(spec=ChannelService)
        mock_svc.resolve_handle.side_effect = ChannelServiceError(
            "API quota exceeded"
        )

        resolver = ChannelResolver(channel_service=mock_svc)
        with pytest.raises(ChannelResolverError, match="API quota exceeded"):
            resolver.resolve("@testchannel")

    def test_network_failure_raises_resolver_error(self):
        mock_svc = MagicMock(spec=ChannelService)
        mock_svc.resolve_handle.side_effect = ChannelServiceError("Network error")

        resolver = ChannelResolver(channel_service=mock_svc)
        with pytest.raises(ChannelResolverError, match="Network error"):
            resolver.resolve("@testchannel")

    def test_invalid_input_raises_before_api_call(self):
        mock_svc = MagicMock(spec=ChannelService)
        resolver = ChannelResolver(channel_service=mock_svc)

        with pytest.raises(InvalidHandleError):
            resolver.resolve("")
        mock_svc.resolve_handle.assert_not_called()
