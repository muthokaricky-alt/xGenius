"""Build data/processed/ from all sources.

    python -m predictor.ingest              # use cache, refresh current season
    python -m predictor.ingest --offline    # cache only, no network refresh

Outputs:
  matches.csv   played domestic matches (football-data.co.uk, with odds)
  fixtures.csv  this season's fixtures + CL results (football-data.org; needs API key)
"""
import sys

from predictor.config import DATA_PROCESSED, is_shown, load_coverage
from predictor.ingest import football_data_org, football_data_uk
from predictor.leagues import LEAGUES
from predictor.teams import resolve


def main(refresh: bool = True):
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    df = football_data_uk.load_all(refresh)
    country = df["league"].map(lambda lg: LEAGUES[lg]["country"])
    df.insert(3, "home_id", [resolve(n, c) for n, c in zip(df["home_raw"], country)])
    df.insert(4, "away_id", [resolve(n, c) for n, c in zip(df["away_raw"], country)])
    unmapped = df[df.home_id.isna() | df.away_id.isna()]
    if len(unmapped):
        raise SystemExit(f"{len(unmapped)} rows with unmapped teams. "
                         "Run: python -m predictor.teams check")
    df = df.drop_duplicates(["date", "league", "home_id", "away_id"])
    df = df.sort_values(["date", "league", "home_id"]).reset_index(drop=True)
    df.to_csv(DATA_PROCESSED / "matches.csv", index=False, date_format="%Y-%m-%d")
    print(f"matches.csv: {len(df):,} matches, {df.date.min():%Y-%m-%d} to {df.date.max():%Y-%m-%d}")

    try:
        fx = football_data_org.load_fixtures()
        cl = football_data_org.load_cl_history()
    except football_data_org.NoApiKey as e:
        print(f"skipping football-data.org: {e}")
        return
    import pandas as pd
    fx = pd.concat([cl, fx], ignore_index=True)
    cov = load_coverage()
    fx["shown"] = [is_shown(lg, h, a, cov) for lg, h, a in zip(fx.league, fx.home_id, fx.away_id)]
    fx.to_csv(DATA_PROCESSED / "fixtures.csv", index=False)
    # Domestic names must all map. CL opponents from leagues we don't ingest
    # (e.g. Shakhtar) are expected to be unmapped until milestone 7.
    dom = fx[fx.league != "champions_league"]
    bad = sorted(set(dom.home_raw[dom.home_id.isna()]) | set(dom.away_raw[dom.away_id.isna()]))
    cl_bad = fx[fx.league == "champions_league"]
    cl_bad = sorted(set(cl_bad.home_raw[cl_bad.home_id.isna()]) | set(cl_bad.away_raw[cl_bad.away_id.isna()]))
    print(f"fixtures.csv: {len(fx):,} rows, {int(fx.shown.sum()):,} shown")
    if bad:
        print(f"  ! unmapped domestic names (add to config/teams.csv): {bad}")
    if cl_bad:
        print(f"  ! unmapped CL teams ({len(cl_bad)}): {cl_bad}")


if __name__ == "__main__":
    main(refresh="--offline" not in sys.argv)
