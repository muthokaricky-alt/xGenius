"""Walk-forward backtest.

    python -m predictor.backtest                  # leaderboard + web/public/data/performance.json
    python -m predictor.backtest --fit-ensemble   # fit the Elo/Dixon-Coles pool on validation
    python -m predictor.backtest --tune           # grid-search Elo on validation
    python -m predictor.backtest --tune-dc        # grid-search Dixon-Coles on validation

How it avoids leaking the future: the model is fitted on everything before
the period, then we step through it one matchday (calendar date) at a time:
predict that day's matches, then reveal their results with update().

Periods (split by date so calendar-year leagues like Norway fit in too):
  burn-in     2014 -> 2016-06-30   ratings settle
  validation  2016-07 -> 2018-06   hyperparameter tuning and ensemble fitting ONLY
  test        2018-07 -> 2026-06   the leaderboard (8 complete seasons)
  season      2026-07 -> today     this season so far, same walk-forward replay
Champions League rows (2023/24 onwards) ride along; they're scored separately
from 2024/25, once a season of CL history exists to link the leagues.

Scored domestic matches: those with Pinnacle closing odds (~92%), so every
model and the market benchmark are compared on exactly the same games. The
market is a reference point, not a model: closing odds aren't known when we'd
publish.
"""
import datetime as dt
import itertools
import json
import sys

import numpy as np
import pandas as pd

from predictor.config import ROOT, is_shown, load_coverage
from predictor.data import CL, load_training
from predictor.metrics import implied_probs, outcome, score_frame
from predictor.models import BaseRate
from predictor.models.dixon_coles import DixonColes
from predictor.models.elo import Elo
from predictor.models.ensemble import PARAMS_PATH, fit_pool, pool
from predictor.config import DATA_PROCESSED

VALIDATION = (pd.Timestamp("2016-07-01"), pd.Timestamp("2018-07-01"))
TEST = (pd.Timestamp("2018-07-01"), pd.Timestamp("2026-07-01"))
CL_SCORED_FROM = pd.Timestamp("2024-07-01")
OUT_DIR = DATA_PROCESSED / "backtest"
WEB_DATA = ROOT / "web" / "public" / "data"
PIN = ["pin_close_h", "pin_close_d", "pin_close_a"]
P = ["p_home", "p_draw", "p_away"]
BLIND = ["date", "season", "league", "home_id", "away_id", "neutral"]  # what predict() may see


def load_matches() -> pd.DataFrame:
    return load_training()


def walk_forward(model, matches: pd.DataFrame, start, end) -> pd.DataFrame:
    model.fit(matches[matches.date < start])
    period = matches[(matches.date >= start) & (matches.date < end)]
    cols = [c for c in BLIND if c in matches]
    chunks = []
    for _, day in period.groupby("date", sort=True):
        p = model.predict(day[cols])
        chunks.append(day.assign(p_home=p[:, 0], p_draw=p[:, 1], p_away=p[:, 2]))
        model.update(day)
    return pd.concat(chunks, ignore_index=True)


def scored(preds: pd.DataFrame) -> pd.DataFrame:
    return preds[preds[PIN].notna().all(axis=1) & (preds[PIN] > 1).all(axis=1)]


def market(preds: pd.DataFrame) -> pd.DataFrame:
    p = implied_probs(*(preds[c] for c in PIN))
    return preds.assign(p_home=p[:, 0], p_draw=p[:, 1], p_away=p[:, 2])


def pooled(elo: pd.DataFrame, dc: pd.DataFrame, params) -> pd.DataFrame:
    p = pool(elo[P].to_numpy(), dc[P].to_numpy(), params, dc.league.eq(CL).to_numpy())
    return dc.assign(p_home=p[:, 0], p_draw=p[:, 1], p_away=p[:, 2])


def calibration(preds: pd.DataFrame, bins=10) -> list[dict]:
    """Forecast probability vs observed frequency, all three outcomes pooled."""
    y = outcome(preds.home_goals, preds.away_goals)
    p = preds[P].to_numpy().ravel()
    hit = (np.eye(3)[y]).ravel()
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    out = []
    for b in range(bins):
        m = idx == b
        if m.sum() >= 30:
            out.append({"forecast": round(float(p[m].mean()), 4),
                        "observed": round(float(hit[m].mean()), 4), "n": int(m.sum())})
    return out


def _fmt(name, s, note=""):
    return (f"| {name} | {s['log_loss']:.4f} | {s['brier']:.4f} | {s['rps']:.4f} "
            f"| {s['accuracy']:.1%} | {note} |")


def _row(key, label, s, note=""):
    return {"key": key, "model": label, "note": note,
            **{k: round(float(v), 4) for k, v in s.items() if k != "n"}, "n": int(s["n"])}


def run():
    matches = load_matches()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    end = pd.Timestamp(dt.date.today())
    preds = {}
    for model in (BaseRate(), Elo(), DixonColes()):
        print(f"backtesting {model.name}...", flush=True)
        preds[model.name] = walk_forward(model, matches, TEST[0], end)
    preds["ensemble"] = pooled(preds["elo"], preds["dixon_coles"], json.loads(PARAMS_PATH.read_text())["params"])
    for name, df in preds.items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d")

    def period(df, a, b):
        return df[(df.date >= a) & (df.date < b)]

    labels = {"ensemble": "Ensemble (Elo + Dixon-Coles)", "dixon_coles": "Dixon-Coles",
              "elo": "Elo", "base_rate": "Base rate"}
    test = {k: scored(period(v[v.league != CL], *TEST)) for k, v in preds.items()}
    mkt = market(test["ensemble"])
    n = len(mkt)
    print(f"\nTest: {TEST[0]:%Y-%m-%d} to {TEST[1]:%Y-%m-%d}, {n:,} matches with Pinnacle closing odds\n")
    print("| Model | Log loss | Brier | RPS | Accuracy | Notes |\n|---|---|---|---|---|---|")
    board = []
    for k in labels:
        s = score_frame(test[k]); board.append(_row(k, labels[k], s))
        print(_fmt(labels[k], s))
    s = score_frame(mkt); board.append(_row("market", "Market (Pinnacle closing)", s, "benchmark only"))
    print(_fmt("market (Pinnacle closing)", s, "benchmark only"))

    by_league = {name: df.groupby("league").apply(lambda g: score_frame(g)["log_loss"], include_groups=False)
                 for name, df in {**test, "market": mkt}.items()}
    by_league = pd.DataFrame(by_league)
    print("\nLog loss by league:\n" + by_league.round(4).to_string())

    cl = {k: v[(v.league == CL) & (v.date >= CL_SCORED_FROM) & (v.date < TEST[1])] for k, v in preds.items()}
    cl_board = [_row(k, labels[k], score_frame(cl[k])) for k in ("ensemble", "dixon_coles", "base_rate")]
    print(f"\nChampions League {CL_SCORED_FROM:%Y}-{TEST[1]:%Y} ({len(cl['ensemble'])} matches):")
    for r in cl_board:
        print(f"  {r['model']:<30} log loss {r['log_loss']:.4f}  accuracy {r['accuracy']:.1%}")

    # This season so far, on the matches the site shows
    cov = load_coverage()
    season = {k: period(v, TEST[1], end) for k, v in preds.items()}
    season = {k: v[[is_shown(l, h, a, cov) for l, h, a in zip(v.league, v.home_id, v.away_id)]]
              for k, v in season.items()}
    season_board = [_row(k, labels[k], score_frame(season[k])) for k in ("ensemble", "base_rate")
                    if len(season[k])]
    if season_board:
        print(f"\nThis season so far ({len(season['ensemble'])} shown matches): "
              f"ensemble log loss {season_board[0]['log_loss']:.4f}, accuracy {season_board[0]['accuracy']:.1%}")

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    perf = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "test": {"from": f"{TEST[0]:%Y-%m-%d}", "to": f"{TEST[1]:%Y-%m-%d}", "matches": n,
                 "leagues": int(mkt.league.nunique()), "leaderboard": board,
                 "by_league": [{"league": lg, **{k: round(float(v), 4) for k, v in row.items()}}
                               for lg, row in by_league.iterrows()],
                 "calibration": calibration(test["ensemble"])},
        "champions_league": {"from": f"{CL_SCORED_FROM:%Y-%m-%d}", "to": f"{TEST[1]:%Y-%m-%d}",
                             "matches": len(cl["ensemble"]), "leaderboard": cl_board},
        "season": {"from": f"{TEST[1]:%Y-%m-%d}", "to": f"{end:%Y-%m-%d}",
                   "matches": len(season["ensemble"]), "leaderboard": season_board},
    }
    (WEB_DATA / "performance.json").write_text(json.dumps(perf, indent=1))
    print(f"\nwrote {WEB_DATA / 'performance.json'}")


def fit_ensemble():
    matches = load_matches()
    elo = walk_forward(Elo(), matches, *VALIDATION)
    dc = walk_forward(DixonColes(), matches, *VALIDATION)
    elo, dc = scored(elo), scored(dc)
    y = outcome(dc.home_goals, dc.away_goals)
    params = fit_pool(elo[P].to_numpy(), dc[P].to_numpy(), y)
    ens = pooled(elo, dc, params)
    for name, df in (("elo", elo), ("dixon_coles", dc), ("ensemble", ens)):
        print(f"validation {name:<12} log loss {score_frame(df)['log_loss']:.5f}")
    PARAMS_PATH.write_text(json.dumps({
        "_comment": "w_elo, w_dc, b_draw, b_away. Fitted on 2016/17-2017/18 by "
                    "`python -m predictor.backtest --fit-ensemble`.",
        "params": [round(float(x), 5) for x in params]}, indent=1) + "\n")
    print("params", [round(float(x), 4) for x in params], "->", PARAMS_PATH)


def tune():
    matches = load_matches()
    # First grid (k 15-30, home_adv 40-80, regress 0.1-0.33, gap 50-150) bottomed out
    # at its lowest edges, so this one extends downward. Best: k=12, regress=0.1,
    # promoted_gap=50 (interior across both grids); home_adv 0 vs 10 vs 20 is noise.
    grid = dict(k=[8, 10, 12, 15], home_adv=[20, 40], regress=[0.0, 0.05, 0.1],
                promoted_gap=[0, 25, 50])
    _grid(Elo, grid, matches)


def tune_dc():
    matches = load_matches()
    # Best: half_life 300-365 (flat), team_ridge 2 (1 and 5 both worse), promoted 0-0.15.
    # group_ridge was chosen on the 2024/25 Champions League instead (10 beat 1, 30, 100, 300),
    # since domestic matches can't see it.
    grid = dict(half_life=[180, 270, 365, 540], team_ridge=[1, 2, 5], promoted=[0.0, 0.1, 0.3])
    _grid(DixonColes, grid, matches)


def _grid(cls, grid, matches):
    results = []
    for values in itertools.product(*grid.values()):
        params = dict(zip(grid, values))
        s = score_frame(scored(walk_forward(cls(**params), matches, *VALIDATION)))
        results.append({**params, **s})
        print(params, f"log loss {s['log_loss']:.4f}", flush=True)
    df = pd.DataFrame(results).sort_values("log_loss")
    print("\nBest on validation:")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    if "--tune" in sys.argv:
        tune()
    elif "--tune-dc" in sys.argv:
        tune_dc()
    elif "--fit-ensemble" in sys.argv:
        fit_ensemble()
    else:
        run()
