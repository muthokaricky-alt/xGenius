"""football-data.co.uk: historical results + bookmaker odds.

Odds columns changed over the years, so we map them into one schema:
  odds_pre_*   market-average odds collected before kickoff (usable as a feature)
  odds_close_* market-average closing odds (benchmark ONLY: not known in advance)
  pin_close_*  Pinnacle closing odds (sharpest benchmark; ONLY for evaluation)
"""
import io
from pathlib import Path

import pandas as pd

from predictor.config import DATA_RAW
from predictor.ingest.cache import fetch
from predictor.leagues import FIRST_SEASON, LEAGUES, current_season

BASE = "https://football-data.co.uk"
RAW_DIR = DATA_RAW / "football-data-uk"
REFRESH_HOURS = 12

# First column found wins (newer name first).
ODDS_SOURCES = {
    "odds_pre":   [("AvgH", "AvgD", "AvgA"), ("BbAvH", "BbAvD", "BbAvA")],
    "odds_close": [("AvgCH", "AvgCD", "AvgCA")],
    "pin_close":  [("PSCH", "PSCD", "PSCA")],
}
OUT_COLUMNS = [
    "date", "season", "league", "home_raw", "away_raw", "home_goals", "away_goals",
    "home_xg", "away_xg",
    "odds_pre_h", "odds_pre_d", "odds_pre_a",
    "odds_close_h", "odds_close_d", "odds_close_a",
    "pin_close_h", "pin_close_d", "pin_close_a",
]


def season_code(season: int) -> str:
    return f"{season % 100:02d}{(season + 1) % 100:02d}"  # 2014 -> "1415"


def _read_csv(path: Path) -> pd.DataFrame:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")  # some old files aren't UTF-8
    # on_bad_lines: a few old files have trailing commas / ragged rows
    return pd.read_csv(io.StringIO(text), on_bad_lines="skip", low_memory=False)


def _normalise(df: pd.DataFrame, league: str, season: int | None) -> pd.DataFrame:
    df = df.rename(columns={"HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG"})
    df = df.dropna(subset=["Home", "Away", "HG", "AG"])
    out = pd.DataFrame({
        # Dates appear as dd/mm/yy and dd/mm/yyyy
        "date": pd.to_datetime(df["Date"], dayfirst=True, format="mixed"),
        "league": league,
        "home_raw": df["Home"].str.strip(),
        "away_raw": df["Away"].str.strip(),
        "home_goals": df["HG"].astype(int),
        "away_goals": df["AG"].astype(int),
        "home_xg": pd.to_numeric(df.get("HxG"), errors="coerce") if "HxG" in df else float("nan"),
        "away_xg": pd.to_numeric(df.get("AxG"), errors="coerce") if "AxG" in df else float("nan"),
    })
    if season is not None:
        out["season"] = season
    else:  # "extra" format has "2012/2013" or "2012" (calendar-year leagues)
        out["season"] = df["Season"].astype(str).str[:4].astype(int)
    for prefix, candidates in ODDS_SOURCES.items():
        cols = next((c for c in candidates if all(x in df for x in c)), None)
        for suffix, i in zip("hda", range(3)):
            out[f"{prefix}_{suffix}"] = pd.to_numeric(df[cols[i]], errors="coerce") if cols else float("nan")
    return out[OUT_COLUMNS]


def load_league(league: str, refresh: bool = True) -> pd.DataFrame:
    meta = LEAGUES[league]
    now = current_season()
    if meta["fduk_format"] == "main":
        frames = []
        for season in range(FIRST_SEASON, now + 1):
            code = season_code(season)
            dest = RAW_DIR / code / f"{meta['fduk']}.csv"
            max_age = REFRESH_HOURS if (season == now and refresh) else None
            try:
                path = fetch(f"{BASE}/mmz4281/{code}/{meta['fduk']}.csv", dest, max_age)
            except Exception as e:  # current season may not be published yet
                if season == now:
                    print(f"  ! {league} {code}: {e}")
                    continue
                raise
            frames.append(_normalise(_read_csv(path), league, season))
        return pd.concat(frames, ignore_index=True)
    # "extra" format: one file, all seasons
    dest = RAW_DIR / "extra" / f"{meta['fduk']}.csv"
    path = fetch(f"{BASE}/new/{meta['fduk']}.csv", dest, REFRESH_HOURS if refresh else None)
    df = _normalise(_read_csv(path), league, None)
    return df[df["season"] >= FIRST_SEASON]


def load_all(refresh: bool = True) -> pd.DataFrame:
    frames = []
    for league, meta in LEAGUES.items():
        if meta["fduk"]:
            print(f"football-data.co.uk: {league}")
            frames.append(load_league(league, refresh))
    return pd.concat(frames, ignore_index=True)
