"""Paths, plus config/coverage.json: which matches the app SHOWS.

Training never uses this filter: a big club's rating depends on its opponents'
ratings, so every match in a covered league is trained on.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COVERAGE_PATH = ROOT / "config" / "coverage.json"
TEAMS_PATH = ROOT / "config" / "teams.csv"
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"


def load_coverage(path: Path = COVERAGE_PATH) -> dict:
    """Big-club names may be any alias in config/teams.csv ("PSG", "Barca"...);
    they're resolved to team_ids so the rest of the code never compares strings."""
    from predictor.leagues import LEAGUES
    from predictor.teams import resolve

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    big = {}
    for league, names in data["big_clubs"].items():
        ids = set()
        for name in names:
            tid = resolve(name, LEAGUES[league]["country"])
            if tid is None:
                raise ValueError(f"coverage.json: unknown team '{name}' in {league}")
            ids.add(tid)
        big[league] = ids
    return {"full_coverage": set(data["full_coverage"]), "big_clubs": big}


def training_leagues(coverage: dict) -> set:
    """Every covered league (full-coverage + big-club leagues)."""
    return coverage["full_coverage"] | set(coverage["big_clubs"])


def is_shown(league: str, home_id: str, away_id: str, coverage: dict) -> bool:
    """True if a match should appear in the app's predictions."""
    if league in coverage["full_coverage"]:
        return True
    clubs = coverage["big_clubs"].get(league, set())
    return home_id in clubs or away_id in clubs
