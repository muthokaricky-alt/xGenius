"""Download-with-cache. Finished seasons never change, so they're fetched once;
current-season files are re-fetched only when older than `max_age_hours`."""
import time
import urllib.request
from pathlib import Path

USER_AGENT = "match-predictor/0.1 (personal research project)"


def is_fresh(dest: Path, max_age_hours: float | None) -> bool:
    if not dest.exists():
        return False
    age_h = (time.time() - dest.stat().st_mtime) / 3600
    return max_age_hours is None or age_h < max_age_hours


def fetch(url: str, dest: Path, max_age_hours: float | None = None,
          headers: dict | None = None, on_response=None) -> Path:
    """Return a local copy of `url`. `max_age_hours=None` means cache forever.
    `on_response(headers)` is called only when the network was actually hit."""
    if is_fresh(dest, max_age_hours):
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
        if on_response:
            on_response(resp.headers)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(body)
    tmp.replace(dest)  # atomic: never leave a half-written cache file
    return dest
