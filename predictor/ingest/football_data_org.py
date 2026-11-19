"""football-data.org API (free tier): upcoming fixtures + Champions League results.

Free tier = 10 requests/minute, so we throttle and cache. Finished seasons are
cached forever; the current season is refreshed every few hours.
"""
import json
import os
import time
import urllib.error

import pandas as pd

from predictor.config import DATA_RAW
from predictor.env import load_env
from predictor.ingest.cache import fetch
from predictor.leagues import FIRST_SEASON, LEAGUES, current_season
from predictor.teams import resolve

BASE = "https://api.football-data.org/v4"
RAW_DIR = DATA_RAW / "football-data-org"
REFRESH_HOURS = 3
MIN_SECONDS_BETWEEN_CALLS = 6.5  # 10/min limit, with margin
_last_call = 0.0


class NoApiKey(RuntimeError):
    pass


def _get(path: str, dest, max_age_hours):
    global _last_call
    load_env()
    key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not key:
        raise NoApiKey("FOOTBALL_DATA_API_KEY not set (see .env.example)")
    if not dest.exists() or max_age_hours is not None:
        wait = MIN_SECONDS_BETWEEN_CALLS - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
    before = dest.stat().st_mtime if dest.exists() else None
    fetch(f"{BASE}{path}", dest, max_age_hours, headers={"X-Auth-Token": key})
    if dest.stat().st_mtime != before:
        _last_call = time.time()
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
