#!/usr/bin/env python3
"""Shared HTTP client for new-api management scripts.

Reads configuration from environment variables:
  NEWAPI_BASE_URL      - Base URL of the new-api instance
  NEWAPI_ACCESS_TOKEN  - Admin access token
  NEWAPI_USER_ID       - Admin user ID (usually "1")
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


class NewAPIClient:
    """Lightweight HTTP client for new-api admin endpoints."""

    def __init__(self, base_url=None, token=None, user_id=None, timeout=30):
        self.base_url = (base_url or os.environ.get("NEWAPI_BASE_URL", "")).rstrip("/")
        self.token = token or os.environ.get("NEWAPI_ACCESS_TOKEN", "")
        self.user_id = user_id or os.environ.get("NEWAPI_USER_ID", "")
        self.timeout = timeout

        if not self.base_url:
            _die("NEWAPI_BASE_URL is not set. Export it or pass --base-url.")
        if not self.token:
            _die("NEWAPI_ACCESS_TOKEN is not set. Export it or pass --token.")
        if not self.user_id:
            _die("NEWAPI_USER_ID is not set. Export it or pass --user-id.")

    # -- public helpers -------------------------------------------------------

    def test_connection(self):
        """Quick health check against /api/status."""
        return self.get("/api/status")

    # -- HTTP verbs -----------------------------------------------------------

    def get(self, path, params=None):
        url = self._url(path, params)
        return self._request("GET", url)

    def post(self, path, body=None, params=None):
        url = self._url(path, params)
        return self._request("POST", url, body)

    def put(self, path, body=None, params=None):
        url = self._url(path, params)
        return self._request("PUT", url, body)

    def delete(self, path, body=None, params=None):
        url = self._url(path, params)
        return self._request("DELETE", url, body)

    # -- internals ------------------------------------------------------------

    def _url(self, path, params=None):
        url = self.base_url + path
        if params:
            # Filter out None values
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                url += "?" + urllib.parse.urlencode(filtered)
        return url

    def _request(self, method, url, body=None):
        headers = {
            "Authorization": self.token,
            "New-Api-User": self.user_id,
            "Content-Type": "application/json",
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"_raw": raw}
        except urllib.error.HTTPError as exc:
            raw = ""
            try:
                raw = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            try:
                detail = json.loads(raw)
            except Exception:
                detail = raw or str(exc)
            _die(f"HTTP {exc.code} {method} {url}\n{ppjson(detail)}")
        except urllib.error.URLError as exc:
            _die(f"Connection failed: {exc.reason}\nURL: {url}")
        except TimeoutError:
            _die(f"Request timed out after {self.timeout}s: {method} {url}")


# -- utility functions (importable) -------------------------------------------

def ppjson(obj):
    """Pretty-print a Python object as JSON."""
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, indent=2, ensure_ascii=False)


def print_json(obj):
    """Print pretty JSON to stdout."""
    print(ppjson(obj))


def _die(msg):
    """Print error message and exit."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def check_success(result):
    """Check if the API response indicates success; exit on failure."""
    if isinstance(result, dict):
        if result.get("success") is False:
            msg = result.get("message", "Unknown error")
            _die(f"API error: {msg}")
    return result


def confirm(prompt="Are you sure? [y/N] "):
    """Ask user for confirmation; return True if they say yes."""
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("y", "yes")


def make_client():
    """Create a NewAPIClient from environment variables."""
    return NewAPIClient()
