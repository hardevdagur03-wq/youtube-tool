"""SSL configuration utilities using certifi's CA bundle.

Provides a centralized SSL context factory used by all HTTP clients
in the application (requests, httplib2, urllib3, etc.).
"""

import logging
import ssl
from typing import Literal

import certifi

logger = logging.getLogger(__name__)

TLSVersion = Literal["TLSv1.2", "TLSv1.3", "auto"]


def create_ssl_context(
    tls_version: TLSVersion = "auto",
    verify_mode: ssl.VerifyMode = ssl.CERT_REQUIRED,
) -> ssl.SSLContext:
    """Create an SSL context using certifi's CA bundle.

    Args:
        tls_version: Minimum TLS version to allow.
            - "TLSv1.2": minimum TLS 1.2 (recommended for YouTube/Google APIs)
            - "TLSv1.3": minimum TLS 1.3
            - "auto": default system behaviour
        verify_mode: Certificate verification mode.

    Returns:
        Configured ``ssl.SSLContext``.
    """
    ctx = ssl.create_default_context(
        capath=None,
        cafile=certifi.where(),
    )
    if tls_version == "TLSv1.2":
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    elif tls_version == "TLSv1.3":
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3

    # Set check_hostname BEFORE verify_mode (must be False if CERT_NONE)
    ctx.check_hostname = verify_mode == ssl.CERT_REQUIRED
    ctx.verify_mode = verify_mode

    return ctx


def get_ca_bundle_path() -> str:
    """Return the path to the CA bundle used by this application."""
    return certifi.where()


def patch_httplib2_ca_certs() -> None:
    """Patch httplib2's default CA certs path to use certifi.

    This ensures httplib2 (used by googleapiclient) validates SSL
    certificates against the same CA bundle as requests/urllib3.
    """
    import httplib2

    ca_path = certifi.where()
    original_init = httplib2.Http.__init__

    def patched_init(self, cache=None, timeout=None, proxy_info=None,
                     ca_certs=None, disable_ssl_certificate_validation=False,
                     tls_maximum_version=None, tls_minimum_version=None, **kwargs):
        if ca_certs is None and not disable_ssl_certificate_validation:
            ca_certs = ca_path
            logger.debug("httplib2.Http using certifi CA bundle: %s", ca_path)
        original_init(
            self,
            cache=cache,
            timeout=timeout,
            proxy_info=proxy_info,
            ca_certs=ca_certs,
            disable_ssl_certificate_validation=disable_ssl_certificate_validation,
            tls_maximum_version=tls_maximum_version,
            tls_minimum_version=tls_minimum_version,
            **kwargs,
        )

    httplib2.Http.__init__ = patched_init
    logger.info("httplib2 patched to use certifi CA bundle: %s", ca_path)
