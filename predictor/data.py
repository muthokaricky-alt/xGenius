"""One training table: domestic results (football-data.co.uk) plus Champions
League results (football-data.org, 2023/24 onwards on the free tier).

Columns: date, season, league, home_id, away_id, home_goals, away_goals,
neutral, home_xg, away_xg, pin_close_*, odds_pre_*. CL rows have no odds.
"""
import pandas as pd

from predictor.config import DATA_PROCESSED
from predictor.leagues import current_season

CL = "champions_league"


def load_fixtures() -> pd.DataFrame:
    path = DATA_PROCESSED / "fixtures.csv"
    if not path.exists():
        return pd.DataFrame()
    fx = pd.read_csv(path, parse_dates=["kickoff"])
    fx["kickoff"] = fx.kickoff.dt.tz_convert("UTC") if fx.kickoff.dt.tz is not None else fx.kickoff
    return fx


def cl_results(fx: pd.DataFrame) -> pd.DataFrame:
    """Finished Champions League matches with both teams mapped (90-minute score)."""
    if fx.empty:
        return pd.DataFrame()
    cl = fx[(fx.league == CL) & (fx.status == "FINISHED")
            & fx.home_id.notna() & fx.away_id.notna() & fx.home_goals.notna()].copy()
    cl["date"] = cl.kickoff.dt.tz_localize(None).dt.normalize()
    cl["season"] = [current_season(d.date()) for d in cl.date]
    cl["neutral"] = cl.stage.eq("FINAL")
    cl["home_goals"] = cl.home_goals.astype(int)
    cl["away_goals"] = cl.away_goals.astype(int)
    return cl[["date", "season", "league", "home_id", "away_id", "home_goals", "away_goals", "neutral"]]


def load_training(include_cl: bool = True) -> pd.DataFrame:
    df = pd.read_csv(DATA_PROCESSED / "matches.csv", parse_dates=["date"])
    df["neutral"] = False
    if include_cl:
        df = pd.concat([df, cl_results(load_fixtures())], ignore_index=True)
    return df.sort_values(["date", "league", "home_id"]).reset_index(drop=True)
