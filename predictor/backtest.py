"""Walk-forward backtest.

    python -m predictor.backtest            # score every model on the test period
    python -m predictor.backtest --tune     # grid-search Elo on the validation period

How it avoids leaking the future: the model is fitted on everything before
the period, then we step through it one matchday (calendar date) at a time:
predict that day's matches, then reveal their results with update().

Periods (split by date so calendar-year leagues like Norway fit in too):
  burn-in     2014 -> 2016-06-30   ratings settle
  validation  2016-07 -> 2018-06   hyperparameter tuning ONLY
  test        2018-07 -> 2026-06   the leaderboard (8 complete seasons)
The current season is left out so leaderboard numbers don't drift week to week.

Scored matches: those with Pinnacle closing odds (~92%), so every model and the
market benchmark are compared on exactly the same games. The market is a
reference point, not a model: closing odds aren't known when we'd publish.
"""
import itertools
import sys

import numpy as np
import pandas as pd

from predictor.config import DATA_PROCESSED
from predictor.metrics import implied_probs, score_frame
from predictor.models import BaseRate
from predictor.models.elo import Elo

VALIDATION = (pd.Timestamp("2016-07-01"), pd.Timestamp("2018-07-01"))
TEST = (pd.Timestamp("2018-07-01"), pd.Timestamp("2026-07-01"))
OUT_DIR = DATA_PROCESSED / "backtest"
PIN = ["pin_close_h", "pin_close_d", "pin_close_a"]


def load_matches() -> pd.DataFrame:
    df = pd.read_csv(DATA_PROCESSED / "matches.csv", parse_dates=["date"])
    return df.sort_values(["date", "league", "home_id"]).reset_index(drop=True)


def walk_forward(model, matches: pd.DataFrame, start, end) -> pd.DataFrame:
    model.fit(matches[matches.date < start])
    period = matches[(matches.date >= start) & (matches.date < end)]
    blind = ["date", "season", "league", "home_id", "away_id"]  # what predict() may see
    chunks = []
    for _, day in period.groupby("date", sort=True):
        p = model.predict(day[blind])
        chunks.append(day.assign(p_home=p[:, 0], p_draw=p[:, 1], p_away=p[:, 2]))
        model.update(day)
    return pd.concat(chunks, ignore_index=True)


def scored(preds: pd.DataFrame) -> pd.DataFrame:
    return preds[preds[PIN].notna().all(axis=1) & (preds[PIN] > 1).all(axis=1)]


def market(preds: pd.DataFrame) -> pd.DataFrame:
    p = implied_probs(*(preds[c] for c in PIN))
    return preds.assign(p_home=p[:, 0], p_draw=p[:, 1], p_away=p[:, 2])


def _fmt(name, s, note=""):
    return (f"| {name} | {s['log_loss']:.4f} | {s['brier']:.4f} | {s['rps']:.4f} "
            f"| {s['accuracy']:.1%} | {note} |")


def run():
    matches = load_matches()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for model in (BaseRate(), Elo()):
        print(f"backtesting {model.name}...")
        preds = scored(walk_forward(model, matches, *TEST))
        preds.to_csv(OUT_DIR / f"{model.name}.csv", index=False, date_format="%Y-%m-%d")
        results[model.name] = preds
    mkt = market(next(iter(results.values())))

    n = len(mkt)
    print(f"\nTest: {TEST[0]:%Y-%m-%d} to {TEST[1]:%Y-%m-%d}, {n:,} matches with Pinnacle closing odds\n")
    print("| Model | Log loss | Brier | RPS | Accuracy | Notes |")
    print("|---|---|---|---|---|---|")
    for name, preds in results.items():
        print(_fmt(name, score_frame(preds)))
    print(_fmt("market (Pinnacle closing)", score_frame(mkt), "benchmark only"))

    print("\nLog loss by league:")
    rows = {name: preds.groupby("league").apply(lambda g: score_frame(g)["log_loss"], include_groups=False)
            for name, preds in {**results, "market": mkt}.items()}
    print(pd.DataFrame(rows).round(4).to_string())


def tune():
    matches = load_matches()
    # First grid (k 15-30, home_adv 40-80, regress 0.1-0.33, gap 50-150) bottomed out
    # at its lowest edges, so this one extends downward. Best: k=12, regress=0.1,
    # promoted_gap=50 (interior across both grids); home_adv 0 vs 10 vs 20 is noise.
    grid = dict(k=[8, 10, 12, 15], home_adv=[20, 40], regress=[0.0, 0.05, 0.1],
                promoted_gap=[0, 25, 50])
    results = []
    for values in itertools.product(*grid.values()):
        params = dict(zip(grid, values))
        s = score_frame(scored(walk_forward(Elo(**params), matches, *VALIDATION)))
        results.append({**params, **s})
        print(params, f"log loss {s['log_loss']:.4f}", flush=True)
    df = pd.DataFrame(results).sort_values("log_loss")
    print("\nBest on validation:")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    tune() if "--tune" in sys.argv else run()
