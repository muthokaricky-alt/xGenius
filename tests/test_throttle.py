"""football-data.org throttling, with a fake clock so nothing really sleeps."""
import io
import json
import urllib.error

import pytest

from predictor.ingest import football_data_org as fdorg
from predictor.ingest.football_data_org import Throttle


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(round(s, 2))
        self.t += s


def headers(remaining, reset):
    return {"X-Requests-Available-Minute": str(remaining), "X-RequestCounter-Reset": str(reset)}


@pytest.fixture
def fc():
    return FakeClock()


@pytest.fixture
def throttle(fc):
    return Throttle(clock=fc.clock, sleep=fc.sleep)


def test_no_wait_while_calls_remain(throttle, fc):
    throttle.before_call()
    throttle.after_response(headers(5, 40))
    fc.t += 0.1
    throttle.before_call()
    assert fc.sleeps == []


def test_waits_for_reset_when_exhausted(throttle, fc):
    throttle.after_response(headers(0, 30))
    fc.t += 10
    throttle.before_call()
    assert fc.sleeps == [21.0]  # 30 s reset + 1 s margin - 10 s already passed


def test_falls_back_to_fixed_spacing_without_headers(throttle, fc):
    throttle.after_response({})
    fc.t += 2
    throttle.before_call()
    assert fc.sleeps == [4.5]


def test_one_missing_header_counts_as_missing(throttle, fc):
    throttle.after_response({"X-Requests-Available-Minute": "0"})
    throttle.before_call()
    assert fc.sleeps == [6.5]


def test_absurd_reset_is_capped(throttle, fc):
    throttle.after_response(headers(0, 99999))
    throttle.before_call()
    assert fc.sleeps == [Throttle.MAX_WAIT]


def _http_error(code, hdrs):
    return urllib.error.HTTPError("u", code, "x", hdrs, io.BytesIO(b""))


def test_429_waits_for_reset_and_retries_once(tmp_path, throttle, fc, monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test")
    dest = tmp_path / "x.json"
    calls = []

    def fake_fetch(url, dest, max_age, headers, on_response):
        calls.append(fc.t)
        if len(calls) == 1:
            raise _http_error(429, {"X-RequestCounter-Reset": "12"})
        dest.write_text(json.dumps({"ok": 1}))
        on_response({"X-Requests-Available-Minute": "9", "X-RequestCounter-Reset": "60"})

    assert fdorg._get("/x", dest, None, throttle, fake_fetch) == {"ok": 1}
    assert fc.sleeps == [13.0] and len(calls) == 2


def test_second_429_raises(tmp_path, throttle, fc, monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "test")

    def always_429(url, dest, max_age, headers, on_response):
        raise _http_error(429, {})

    with pytest.raises(urllib.error.HTTPError):
        fdorg._get("/x", tmp_path / "x.json", None, throttle, always_429)
    assert fc.sleeps == [61.0]  # no reset header: a full minute + margin


def test_cache_hit_makes_no_call(tmp_path, throttle, fc):
    dest = tmp_path / "x.json"
    dest.write_text('{"cached": true}')

    def boom(*a, **k):
        raise AssertionError("network hit")

    assert fdorg._get("/x", dest, None, throttle, boom) == {"cached": True}
