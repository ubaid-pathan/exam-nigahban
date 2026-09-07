"""Verify a deployed Exam Nigahban instance from the outside.

Why this exists
---------------
Two settings are invisible in the code and only wrong once deployed, and
both fail in ways that look like something else:

  * CORS_ORIGINS on the API must contain the frontend's EXACT origin. If it
    does not, every API call from the deployed site fails while everything
    works perfectly from localhost -- and the browser reports it as a
    network error, not as a configuration problem.

  * VITE_API_BASE_URL is baked into the frontend at BUILD time, so it
    cannot be corrected by changing an environment variable afterwards. If
    it is http:// rather than https://, the student session WebSocket
    derives ws:// instead of wss://, and the browser silently blocks it as
    mixed content -- real-time pause and cancellation stop arriving, while
    the eight-second polling fallback quietly covers for it.

Checking these by reading dashboards is easy to get subtly wrong. This
makes the requests a browser would actually make and reports what came
back.

Read-only: it issues GET and OPTIONS requests and changes nothing.

Usage
-----
    python check_deployment.py https://your-api.onrender.com https://your-app.vercel.app

Exits 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

TIMEOUT = 60  # Render's free tier cold-starts; the first request can be slow.

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"

_results: list[tuple[str, str]] = []


def record(status: str, message: str) -> None:
    _results.append((status, message))
    print(f"  [{status}] {message}")


def request(url: str, method: str = "GET", headers: dict | None = None):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    # Default context; a deployment with a broken certificate SHOULD fail
    # here rather than be waved through.
    return urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context())


def check_api_reachable(api: str) -> bool:
    print("\nAPI")
    try:
        with request(f"{api}/health") as response:
            body = json.loads(response.read())
        if body.get("status") == "ok":
            record(PASS, f"/health responded ok ({body.get('service', 'unknown service')})")
            return True
        record(FAIL, f"/health returned unexpected body: {body}")
    except urllib.error.HTTPError as exc:
        record(FAIL, f"/health returned HTTP {exc.code}")
    except Exception as exc:  # noqa: BLE001 - any failure is a failure to report
        record(FAIL, f"/health unreachable: {type(exc).__name__}: {exc}")
    return False


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def is_local(url: str) -> bool:
    return (urlparse(url).hostname or "") in LOCAL_HOSTS


def check_scheme(api: str, frontend: str) -> None:
    """A remote deployment must be https, or the WebSocket cannot connect.

    localhost is exempt: browsers treat it as a secure context, so
    http://localhost is a legitimate development setup and ws:// works
    there. Flagging it would make every local run look broken.
    """
    print("\nTransport")
    for label, url in (("API", api), ("frontend", frontend)):
        scheme = urlparse(url).scheme
        if scheme == "https":
            record(PASS, f"{label} is served over https")
        elif is_local(url):
            record(PASS, f"{label} is local ({scheme}://) -- a secure context in browsers")
        else:
            record(
                FAIL,
                f"{label} is {scheme}:// on a remote host -- the student WebSocket "
                "will be blocked as mixed content",
            )


def check_cors(api: str, frontend: str) -> None:
    """The check that catches the most common deployment failure.

    A preflight is what the browser actually sends before a cross-origin
    request carrying an Authorization header, so this reproduces the real
    condition rather than approximating it.
    """
    print("\nCORS")
    origin = frontend.rstrip("/")
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    }
    try:
        with request(f"{api}/api/auth/me", method="OPTIONS", headers=headers) as response:
            allow_origin = response.headers.get("Access-Control-Allow-Origin")
            allow_creds = response.headers.get("Access-Control-Allow-Credentials")
    except urllib.error.HTTPError as exc:
        allow_origin = exc.headers.get("Access-Control-Allow-Origin")
        allow_creds = exc.headers.get("Access-Control-Allow-Credentials")
    except Exception as exc:  # noqa: BLE001
        record(FAIL, f"preflight failed: {type(exc).__name__}: {exc}")
        return

    if allow_origin in (origin, "*"):
        record(PASS, f"API allows origin {origin}")
        if allow_origin == "*" and allow_creds == "true":
            record(
                WARN,
                "wildcard origin with credentials is rejected by browsers -- "
                "set CORS_ORIGINS to the exact origin",
            )
    elif allow_origin:
        record(FAIL, f"API allows '{allow_origin}', not '{origin}' -- CORS_ORIGINS mismatch")
    else:
        record(
            FAIL,
            f"API sent no Access-Control-Allow-Origin for {origin} -- "
            "add it to CORS_ORIGINS",
        )


def check_frontend(frontend: str, api: str) -> None:
    """Reads the built bundle to see which API URL was compiled into it.

    VITE_API_BASE_URL is substituted at build time, so the deployed
    JavaScript is the only place the real value can be confirmed --
    changing the environment variable without rebuilding does nothing.
    """
    print("\nFrontend")
    try:
        with request(frontend) as response:
            html = response.read().decode("utf-8", "replace")
        record(PASS, "index.html served")
    except Exception as exc:  # noqa: BLE001
        record(FAIL, f"frontend unreachable: {type(exc).__name__}: {exc}")
        return

    # Vite emits a single hashed entry bundle referenced from index.html.
    import re

    match = re.search(r'src="(/assets/[^"]+\.js)"', html)
    if not match:
        record(WARN, "could not locate the JS bundle in index.html -- skipping API URL check")
        return

    bundle_url = frontend.rstrip("/") + match.group(1)
    try:
        with request(bundle_url) as response:
            bundle = response.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        record(WARN, f"could not read the JS bundle: {type(exc).__name__}: {exc}")
        return

    expected = api.rstrip("/")
    if expected in bundle:
        record(PASS, f"bundle was built against {expected}")
    elif "127.0.0.1:8000" in bundle or "localhost:8000" in bundle:
        record(
            FAIL,
            "bundle was built against localhost -- VITE_API_BASE_URL was not set "
            "at BUILD time; set it and redeploy the frontend",
        )
    else:
        record(
            WARN,
            f"could not find {expected} in the bundle; confirm VITE_API_BASE_URL "
            "manually (it may be minified differently)",
        )


def check_model(frontend: str) -> None:
    """The phone-detection model is a shipped static asset."""
    print("\nPhone-detection model")
    url = frontend.rstrip("/") + "/models/yolox-nano-phone.onnx"
    try:
        # Some static hosts refuse HEAD; a ranged GET works everywhere and
        # still avoids downloading 3.7 MB just to confirm it exists.
        req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            content_range = response.headers.get("Content-Range") or ""
            size = (
                int(content_range.rsplit("/", 1)[-1])
                if "/" in content_range
                else int(response.headers.get("Content-Length") or 0)
            )
        if size > 3_000_000:
            record(PASS, f"model served, {size:,} bytes")
        else:
            record(WARN, f"model served but only {size:,} bytes -- expected ~3.7 MB")
    except urllib.error.HTTPError as exc:
        record(
            FAIL,
            f"model returned HTTP {exc.code} -- phone detection will not work; "
            "check it was committed and the build copied public/",
        )
    except Exception as exc:  # noqa: BLE001
        record(FAIL, f"model unreachable: {type(exc).__name__}: {exc}")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1

    api = sys.argv[1].rstrip("/")
    frontend = sys.argv[2].rstrip("/")

    print(f"API:      {api}")
    print(f"Frontend: {frontend}")
    print("\nThe first request may take up to a minute if the API has cold-started.")

    check_scheme(api, frontend)
    if check_api_reachable(api):
        check_cors(api, frontend)
    check_frontend(frontend, api)
    check_model(frontend)

    failures = sum(1 for status, _ in _results if status == FAIL)
    warnings = sum(1 for status, _ in _results if status == WARN)

    print("\n" + "-" * 60)
    if failures:
        print(f"RESULT: {failures} check(s) FAILED, {warnings} warning(s).")
        return 1
    print(f"RESULT: all checks passed ({warnings} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
