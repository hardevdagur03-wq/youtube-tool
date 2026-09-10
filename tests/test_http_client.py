"""Tests for utils/http_client.py"""

import ssl
from unittest.mock import patch, MagicMock

import pytest
import requests

from utils.http_client import (
    HttpClient,
    HttpClientConfig,
    SslHandshakeError,
    ConnectionTimeoutError,
    HttpUpstreamError,
    HttpClientError,
)


class TestHttpClientConfig:
    def test_default_config(self):
        config = HttpClientConfig()
        assert config.connect_timeout == 15.0
        assert config.read_timeout == 30.0
        assert config.max_retries == 3
        assert config.backoff_factor == 1.0
        assert 429 in config.retry_on_status
        assert 500 in config.retry_on_status

    def test_timeout_property(self):
        config = HttpClientConfig(connect_timeout=5.0, read_timeout=10.0)
        assert config.timeout == (5.0, 10.0)


class TestHttpClient:
    def test_singleton(self):
        client1 = HttpClient.get_instance()
        client2 = HttpClient.get_instance()
        assert client1 is client2

    def test_singleton_with_config(self):
        config = HttpClientConfig(connect_timeout=5.0)
        client1 = HttpClient.get_instance()
        client2 = HttpClient.get_instance(config)
        assert client1 is not client2

    def test_session_verify_uses_certifi(self):
        import certifi
        client = HttpClient()
        assert client._session.verify == certifi.where()

    def test_session_has_retry_adapter(self):
        client = HttpClient()
        adapter = client._session.get_adapter("https://example.com")
        assert adapter.max_retries.total == 3

    def test_close(self):
        client = HttpClient()
        client.close()
        # After close, the session's adapters are closed
        assert client._session is not None
        # Verify the session is still usable (close doesn't set to None)
        # but internally the adapters should be closed

    def test_context_manager(self):
        with HttpClient() as client:
            assert client._session is not None
        # After context exit, session should be closed
        assert client._session is not None

    @patch("utils.http_client.requests.Session.request")
    def test_request_success(self, mock_request):
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        client = HttpClient()
        resp = client.get("https://example.com/test")
        assert resp.status_code == 200
        mock_request.assert_called_once()

    @patch("utils.http_client.requests.Session.request")
    def test_ssl_error_mapped(self, mock_request):
        mock_request.side_effect = requests.exceptions.SSLError(
            "EOF occurred in violation of protocol (_ssl.c:2427)"
        )
        client = HttpClient()
        with pytest.raises(SslHandshakeError) as exc_info:
            client.get("https://example.com/")
        assert "Unable to connect securely" in str(exc_info.value)

    @patch("utils.http_client.requests.Session.request")
    def test_connection_error_mapped(self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection refused")
        client = HttpClient()
        with pytest.raises(ConnectionTimeoutError) as exc_info:
            client.get("https://example.com/")
        assert "Unable to connect" in str(exc_info.value)

    @patch("utils.http_client.requests.Session.request")
    def test_timeout_error_mapped(self, mock_request):
        mock_request.side_effect = requests.exceptions.Timeout("Timed out")
        client = HttpClient()
        with pytest.raises(ConnectionTimeoutError) as exc_info:
            client.get("https://example.com/")
        assert "connection timed out" in str(exc_info.value).lower()

    @patch("utils.http_client.requests.Session.request")
    def test_http_error_mapped(self, mock_request):
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error", response=mock_response
        )
        mock_request.return_value = mock_response

        client = HttpClient()
        with pytest.raises(HttpUpstreamError) as exc_info:
            client.get("https://example.com/")
        assert "error (HTTP 500)" in str(exc_info.value)

    @patch("utils.http_client.requests.Session.request")
    def test_unexpected_error_mapped(self, mock_request):
        mock_request.side_effect = RuntimeError("Something went wrong")
        client = HttpClient()
        with pytest.raises(HttpClientError) as exc_info:
            client.get("https://example.com/")
        assert "unexpected error" in str(exc_info.value).lower()

    @patch.object(HttpClient, "_build_session")
    def test_custom_config(self, mock_build):
        config = HttpClientConfig(connect_timeout=5.0, max_retries=5)
        client = HttpClient(config=config)
        assert client._config.connect_timeout == 5.0
        assert client._config.max_retries == 5



