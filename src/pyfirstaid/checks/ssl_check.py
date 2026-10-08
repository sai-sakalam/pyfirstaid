"""Check: can this Python make verified HTTPS connections to PyPI?"""

from __future__ import annotations

import os
import sys
from typing import List

from pyfirstaid.model import Finding, Options, Status

CHECK_ID = "ssl"

CERT_ENV_VARS = ("SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
                 "CURL_CA_BUNDLE", "PIP_CERT")
PROXY_ENV_VARS = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")
TEST_URL = "https://pypi.org/simple/pip/"

CORPORATE_FIX = (
    "If you are behind a company proxy or VPN, it is probably inspecting HTTPS traffic. "
    "Ask IT for the company root certificate (.pem), then run: "
    "python -m pip config set global.cert /path/to/company-ca.pem  "
    "(also: set SSL_CERT_FILE=/path/to/company-ca.pem). "
    "Upgrading pip can also help: python -m pip install --upgrade pip"
)


def bad_cert_env_vars(environ=os.environ) -> List[str]:
    """Return env vars that point at certificate files/dirs that do not exist."""
    return [name for name in CERT_ENV_VARS
            if environ.get(name) and not os.path.exists(environ[name])]


def classify_error(exc: BaseException) -> str:
    """Map a connection exception to 'cert', 'ssl' or 'network'."""
    import ssl

    reason = getattr(exc, "reason", exc)
    if (isinstance(reason, ssl.SSLCertVerificationError)
            or "CERTIFICATE_VERIFY_FAILED" in str(reason)):
        return "cert"
    if isinstance(reason, ssl.SSLError):
        return "ssl"
    return "network"


def run_check(opts: Options) -> List[Finding]:
    try:
        import ssl
    except ImportError:
        return [Finding(
            CHECK_ID, Status.ERROR, "This Python was built WITHOUT SSL support",
            detail="`import ssl` failed, so pip cannot download anything.",
            fix="Reinstall Python from python.org or your package manager "
                "(if you compiled it yourself, install the OpenSSL dev package first).",
        )]

    findings: List[Finding] = []
    for name in bad_cert_env_vars():
        findings.append(Finding(
            CHECK_ID, Status.ERROR, "%s points to a file that does not exist" % name,
            detail="%s=%s" % (name, os.environ[name]),
            fix="Fix the path, or remove the variable (unset %s)." % name,
        ))

    paths = ssl.get_default_verify_paths()
    no_ca = not ((paths.cafile and os.path.exists(paths.cafile))
                 or (paths.capath and os.path.isdir(paths.capath) and os.listdir(paths.capath)))
    if sys.platform == "darwin" and no_ca and not os.environ.get("SSL_CERT_FILE"):
        findings.append(Finding(
            CHECK_ID, Status.WARN, "No CA certificates configured for this macOS Python",
            detail="python.org installers on macOS need a one-time certificate install.",
            fix='Run: open "/Applications/Python %d.%d/Install Certificates.command"'
                % sys.version_info[:2],
        ))

    if opts.offline:
        findings.append(Finding(CHECK_ID, Status.SKIP,
                                "Skipped connection test to pypi.org (--offline)"))
        return findings

    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(TEST_URL, method="HEAD",
                                     headers={"User-Agent": "pyfirstaid"})
        with urllib.request.urlopen(req, timeout=opts.timeout,
                                    context=ssl.create_default_context()):
            pass
        findings.append(Finding(CHECK_ID, Status.OK,
                                "HTTPS to pypi.org works (%s)" % ssl.OPENSSL_VERSION))
    except urllib.error.HTTPError as exc:
        # The TLS handshake and certificate check succeeded; the server (or a
        # proxy) answered with an HTTP error code.
        findings.append(Finding(
            CHECK_ID, Status.INFO,
            "SSL certificates OK, but pypi.org answered HTTP %s" % exc.code,
            detail="A proxy or firewall may be blocking PyPI." if exc.code in (403, 407) else "",
            fix="If pip installs fail, check your proxy settings or ask IT to allow pypi.org "
                "and files.pythonhosted.org.",
        ))
    except Exception as exc:  # noqa: BLE001 - we classify every failure
        kind = classify_error(exc)
        if kind == "cert":
            findings.append(Finding(
                CHECK_ID, Status.ERROR, "SSL certificate verification FAILED for pypi.org",
                detail=str(exc)[:300], fix=CORPORATE_FIX,
            ))
        elif kind == "ssl":
            findings.append(Finding(
                CHECK_ID, Status.ERROR, "SSL error connecting to pypi.org",
                detail=str(exc)[:300], fix=CORPORATE_FIX,
            ))
        else:
            proxies = [v for v in PROXY_ENV_VARS if os.environ.get(v)]
            findings.append(Finding(
                CHECK_ID, Status.WARN, "Could not reach pypi.org",
                detail=str(exc)[:300] + (
                    "\nProxy variables set: %s" % ", ".join(proxies) if proxies else ""),
                fix="Check your internet connection, VPN or proxy settings. "
                    "Use --offline to skip this test.",
            ))
    return findings
