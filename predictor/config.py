"""Loads config/coverage.json and decides which matches are shown in the app.

Training never uses this filter: a big club's rating depends on its opponents'
ratings, so every match in a covered league is trained on.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COVERAGE_PATH = ROOT / "config" / "coverage.json"


def load_coverage(path: Path = COVERAGE_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {
        "full_coverage": set(data["full_coverage"]),
        "big_clubs": {lg: set(teams) for lg, teams in data["big_clubs"].items()},
    }


def training_leagues(coverage: dict) -> set:
    """Every league we need data for (full-coverage + big-club leagues)."""
    return coverage["full_coverage"] | set(coverage["big_clubs"])


def is_shown(league: str, home: str, away: str, coverage: dict) -> bool:
    """True if a match should appear in the app's predictions."""
    if league in coverage["full_coverage"]:
        return True
    clubs = coverage["big_clubs"].get(league, set())
    return home in clubs or away in clubs
