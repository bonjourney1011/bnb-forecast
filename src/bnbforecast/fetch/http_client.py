"""Polite HTTP helpers: generic UA, retries, robots.txt hard stop, per-host throttle."""

from __future__ import annotations

import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

USER_AGENT = "bnb-forecast-bot/0.1 (market data research)"
TIMEOUT = 30
RETRIES = 3
DEFAULT_SPACING = 1.0  # seconds between requests to the same host

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})
_last_hit: dict[str, float] = {}
_robots: dict[str, object | None] = {}


class RobotsDisallowed(RuntimeError):
    """Raised when robots.txt forbids the URL for our user agent."""


def min_interval(host: str, seconds: float) -> None:
    """Sleep so that consecutive hits to `host` are at least `seconds` apart."""
    wait = _last_hit.get(host, 0.0) + seconds - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.monotonic()


class _DisallowAll:
    @staticmethod
    def can_fetch(_agent: str, _url: str) -> bool:
        return False


def robots_allows(url: str) -> bool:
    """RFC 9309: robots.txt 2xx -> follow its rules; 4xx (missing) -> allowed; 5xx or
    unreachable -> disallowed (cached for the session)."""
    parts = urlparse(url)
    host = f"{parts.scheme}://{parts.netloc}"
    if host not in _robots:
        rp = _DisallowAll()
        try:
            min_interval(parts.netloc, DEFAULT_SPACING)
            r = _session.get(f"{host}/robots.txt", timeout=TIMEOUT)
            if 400 <= r.status_code < 500:
                rp = None
            elif r.status_code == 200:
                if "html" in r.headers.get("content-type", "").lower():
                    rp = None  # SPA catch-all page, not a robots file
                else:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.parse(r.text.splitlines())
        except requests.RequestException:
            pass
        _robots[host] = rp
    rp = _robots[host]
    return True if rp is None else rp.can_fetch("*", url)


def _request(method: str, url: str, spacing: float, **kw) -> requests.Response:
    if not robots_allows(url):
        raise RobotsDisallowed(url)
    host = urlparse(url).netloc
    last: Exception | None = None
    for attempt in range(RETRIES):
        min_interval(host, spacing)
        try:
            r = _session.request(method, url, timeout=TIMEOUT, **kw)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()  # other 4xx: client error, not retried
            return r
        except requests.HTTPError as e:
            last = e
            code = e.response.status_code if e.response is not None else 0
            if 400 <= code < 500 and code != 429:
                raise RuntimeError(f"HTTP {code}: {url}") from e
        except requests.RequestException as e:
            last = e
        if attempt < RETRIES - 1:
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"request failed after {RETRIES} tries: {url}: {last}")


def get_json(url: str, params: dict | None = None, spacing: float = DEFAULT_SPACING):
    return _request("GET", url, spacing, params=params).json()


def post_form(url: str, data: dict, spacing: float = DEFAULT_SPACING):
    return _request("POST", url, spacing, data=data).json()


def get_text(url: str, spacing: float = DEFAULT_SPACING) -> str:
    r = _request("GET", url, spacing)
    r.encoding = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else "utf-8"
    return r.text
