"""football-data.org API (free tier): upcoming fixtures + Champions League results.

Rate limiting follows the API's own headers rather than a fixed delay:
  X-Requests-Available-Minute  calls left in the current window
  X-RequestCounter-Reset       seconds until that window resets
If a response lacks them we fall back to spacing calls 6.5 s apart (10/min with
margin). A 429 waits until the reset time and retries once.

Finished seasons are cached forever; the current season every few hours.
"""
import json
import os
import time
import urllib.error

import pandas as pd

from predictor.config import DATA_RAW
from predictor.env import load_env
from predictor.ingest.cache import fetch, is_fresh
from predictor.leagues import FIRST_SEASON, LEAGUES, current_season
from predictor.teams import resolve

BASE = "https://api.football-data.org/v4"
RAW_DIR = DATA_RAW / "football-data-org"
REFRESH_HOURS = 3


class NoApiKey(RuntimeError):
    pass


def _header_int(headers, name):
    try:
        return int(headers.get(name))
    except (TypeError, ValueError):
        return None


class Throttle:
    """Waits only when the API says we're out of calls for this minute."""
    FALLBACK_SPACING = 6.5   # seconds between calls when headers are missing
    DEFAULT_RESET = 60       # 429 without a reset header: wait a full window
    MAX_WAIT = 120           # never trust a reset value beyond this
    MARGIN = 1.0             # reset header is whole seconds; don't arrive early

    def __init__(self, clock=time.monotonic, sleep=time.sleep):
        self.clock, self.sleep = clock, sleep
        self.last_call = None
        self.remaining = None   # None = no header info: use fallback spacing
        self.reset_at = None

    def _wait_until(self, t):
        delay = min(t - self.clock(), self.MAX_WAIT)
        if delay > 0:
            self.sleep(delay)

    def before_call(self):
        if self.remaining is not None:
            if self.remaining <= 0:
                self._wait_until(self.reset_at)
        elif self.last_call is not None:
            self._wait_until(self.last_call + self.FALLBACK_SPACING)

    def after_response(self, headers):
        self.last_call = self.clock()
        remaining = _header_int(headers, "X-Requests-Available-Minute")
        reset = _header_int(headers, "X-RequestCounter-Reset")
        if remaining is None or reset is None:
            self.remaining = self.reset_at = None
        else:
            self.remaining = remaining
            self.reset_at = self.last_call + reset + self.MARGIN

    def on_429(self, headers):
        reset = _header_int(headers, "X-RequestCounter-Reset")
        self.last_call = self.clock()
        self._wait_until(self.last_call + (self.DEFAULT_RESET if reset is None else reset) + self.MARGIN)
        self.remaining = self.reset_at = None  # unknown until the retry answers


_throttle = Throttle()


def _get(path: str, dest, max_age_hours, throttle: Throttle = None, fetch_fn=fetch):
    throttle = throttle or _throttle
    if not is_fresh(dest, max_age_hours):
        load_env()
        key = os.environ.get("FOOTBALL_DATA_API_KEY")
        if not key:
            raise NoApiKey("FOOTBALL_DATA_API_KEY not set (see .env.example)")
        for attempt in (1, 2):
            throttle.before_call()
            try:
                fetch_fn(f"{BASE}{path}", dest, max_age_hours, headers={"X-Auth-Token": key},
                         on_response=throttle.after_response)
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 1:
                    print(f"  rate-limited on {path}; waiting for reset, then retrying once")
                    throttle.on_429(e.headers)
                    continue
                throttle.after_response(e.headers or {})
                raise
    return json.loads(dest.read_text(encoding="utf-8"))


def parse_matches(payload: dict, league: str) -> pd.DataFrame:
    """Flatten the API's match list. Goals are the 90-minute score: in knockout
    ties the API's `fullTime` includes extra time (and sometimes shootouts),
    which would distort a model of normal-time goals."""
    country = LEAGUES[league]["country"]  # None for the Champions League
    rows = []
    for m in payload.get("matches", []):
        score = m.get("score", {})
        regular = score.get("regularTime") or score.get("fullTime") or {}
        home, away = m["homeTeam"].get("name") or "", m["awayTeam"].get("name") or ""
        rows.append({
            "match_id": m["id"],
            "kickoff": m["utcDate"],
            "status": m["status"],
            "league": league,
            "stage": m.get("stage"),
            "home_raw": home,
            "away_raw": away,
            "home_id": resolve(home, country),
            "away_id": resolve(away, country),
            "home_goals": regular.get("home"),
            "away_goals": regular.get("away"),
        })
    return pd.DataFrame(rows)


def load_competition(league: str, season: int) -> pd.DataFrame:
    code = LEAGUES[league]["fdorg"]
    max_age = REFRESH_HOURS if season == current_season() else None
    dest = RAW_DIR / f"{code}_{season}.json"
    payload = _get(f"/competitions/{code}/matches?season={season}", dest, max_age)
    return parse_matches(payload, league)


def load_fixtures() -> pd.DataFrame:
    """This season's matches (played + upcoming) for every league on the API."""
    frames = [load_competition(lg, current_season())
              for lg, meta in LEAGUES.items() if meta["fdorg"]]
    return pd.concat(frames, ignore_index=True)


def load_cl_history() -> pd.DataFrame:
    """Past Champions League seasons. The free tier may not serve all of them;
    we keep what it allows and report the rest."""
    frames, denied = [], []
    for season in range(FIRST_SEASON, current_season()):
        try:
            frames.append(load_competition("champions_league", season))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                denied.append(season)
                continue
            raise
    if denied:
        print(f"  ! Champions League seasons not on free tier: {denied}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def parse_scorers(payload: dict, league: str) -> pd.DataFrame:
    """Top scorers of one competition. The API lists only players with at
    least one goal, and gives null (not 0) for missing assists/penalties."""
    country = LEAGUES[league]["country"]
    rows = []
    for s in payload.get("scorers", []):
        team = s.get("team", {}).get("name") or ""
        player = s.get("player", {})
        rows.append({
            "league": league,
            "player_id": player.get("id"),
            "player": player.get("name"),
            "team_raw": team,
            "team_id": resolve(team, country),
            "goals": s.get("goals") or 0,
            "assists": s.get("assists") or 0,
            "penalties": s.get("penalties") or 0,
            "played": s.get("playedMatches") or 0,
        })
    return pd.DataFrame(rows)


def load_scorers() -> pd.DataFrame:
    """This season's top 100 scorers for every competition on the API."""
    season = current_season()
    frames = []
    for lg, meta in LEAGUES.items():
        if not meta["fdorg"]:
            continue
        code = meta["fdorg"]
        if lg not in ("premier_league", "champions_league", "la_liga", "bundesliga", "serie_a", "ligue_1"):
            continue  # races are only published for the competitions the site shows
        dest = RAW_DIR / f"{code}_{season}_scorers.json"
        payload = _get(f"/competitions/{code}/scorers?season={season}&limit=100", dest, REFRESH_HOURS)
        frames.append(parse_scorers(payload, lg))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
