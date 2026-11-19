"""Walk-forward backtest.

    python -m predictor.backtest                  # leaderboard, performance.json, config/ensemble.json
    python -m predictor.backtest --tune           # grid-search Elo on validation
    python -m predictor.backtest --tune-dc        # grid-search Dixon-Coles on validation

How it avoids leaking the future: the model is fitted on everything before
the period, then we step through it one matchday (calendar date) at a time:
predict that day's matches, then reveal their results with update().

Periods (split by date so calendar-year leagues like Norway fit in too):
  burn-in     2014 -> 2016-06-30   ratings settle
  validation  2016-07 -> 2018-06   hyperparameter tuning ONLY
  test        2018-07 -> 2026-06   the leaderboard (8 complete seasons)
The ensemble pools are refitted before every test season on the walk-forward
predictions of the seasons before it (never on the season being scored);
config/ensemble.json, used live, is fitted on everything before this season.
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
from predictor.models.ensemble import PARAMS_PATH, combine, fit_params, pool_stats
from predictor.config import DATA_PROCESSED

VALIDATION = (pd.Timestamp("2016-07-01"), pd.Timestamp("2018-07-01"))
TEST = (pd.Timestamp("2018-07-01"), pd.Timestamp("2026-07-01"))
CL_SCORED_FROM = pd.Timestamp("2024-07-01")
OUT_DIR = DATA_PROCESSED / "backtest"
WEB_DATA = ROOT / "web" / "public" / "data"
PIN = ["pin_close_h", "pin_close_d", "pin_close_a"]
PRE = ["odds_pre_h", "odds_pre_d", "odds_pre_a"]
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


def season_start(d: pd.Series) -> pd.Series:
    return pd.to_datetime((d.dt.year.where(d.dt.month >= 7, d.dt.year - 1)).astype(str) + "-07-01")


def ensemble_preds(elo: pd.DataFrame, dc: pd.DataFrame, start) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Expanding-window ensemble from `start`: each season scored with pools
    fitted only on earlier seasons. Returns (full ensemble, stats-only, params
    fitted on everything before the latest season)."""
    key = ["date", "league", "home_id", "away_id"]
    E = ["e_h", "e_d", "e_a"]
    d = dc.merge(elo[key + P].rename(columns=dict(zip(P, E))), on=key)
    y = outcome(d.home_goals, d.away_goals)
    is_cl = d.league.eq(CL).to_numpy()
    starts = season_start(d.date)
    pe, pd_ = d[E].to_numpy(), d[P].to_numpy()
    odds = d[PRE].to_numpy(float) if set(PRE) <= set(d) else np.full((len(d), 3), np.nan)
    full = np.full((len(d), 3), np.nan)
    stats = np.full((len(d), 3), np.nan)
    used = np.zeros(len(d), bool)
    params = None
    for s in sorted(starts[d.date >= start].unique()):
        tr = (d.date < s).to_numpy()
        rows = (starts == s).to_numpy()
        params = fit_params(pe[tr], pd_[tr], odds[tr], is_cl[tr], y[tr])
        full[rows], used[rows] = combine(pe[rows], pd_[rows], odds[rows], is_cl[rows], params)
        stats[rows] = pool_stats(pe[rows], pd_[rows], params["stats"], is_cl[rows])
    keep = (d.date >= start).to_numpy()
    base = d.drop(columns=E)
    ens = base.assign(p_home=full[:, 0], p_draw=full[:, 1], p_away=full[:, 2], used_market=used)[keep]
    ens_stats = base.assign(p_home=stats[:, 0], p_draw=stats[:, 1], p_away=stats[:, 2])[keep]
    return ens.reset_index(drop=True), ens_stats.reset_index(drop=True), params


def market_pre(preds: pd.DataFrame) -> pd.DataFrame:
    ok = preds[PRE].notna().all(axis=1) & (preds[PRE] > 1).all(axis=1)
    p = implied_probs(*(preds.loc[ok, c] for c in PRE))
    return preds[ok].assign(p_home=p[:, 0], p_draw=p[:, 1], p_away=p[:, 2])


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
    end = pd.Timestamp(dt.date.today()) + pd.Timedelta(days=1)
    preds = {}
    for model in (BaseRate(), Elo(), DixonColes()):
        print(f"backtesting {model.name}...", flush=True)
        preds[model.name] = walk_forward(model, matches, VALIDATION[0], end)
    print("fitting ensembles season by season...", flush=True)
    preds["ensemble"], preds["ensemble_stats"], live = ensemble_preds(preds["elo"], preds["dixon_coles"], TEST[0])
    for name, df in preds.items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    PARAMS_PATH.write_text(json.dumps({
        "_comment": "Fitted by `python -m predictor.backtest` on all walk-forward predictions before this "
                    "season. stats: w_elo, w_dc, b_draw, b_away, cl_b_draw, cl_b_away. "
                    "market: w_elo, w_dc, w_market, b_draw, b_away.",
        "stats": [round(x, 5) for x in live["stats"]], "market": [round(x, 5) for x in live["market"]]},
        indent=1) + "\n")

    def period(df, a, b):
        return df[(df.date >= a) & (df.date < b)]

    labels = {"ensemble": "xGenius", "ensemble_stats": "xGenius, stats only", "dixon_coles": "Dixon-Coles",
              "elo": "Elo", "base_rate": "Base rate"}
    notes = {"ensemble": "Elo + Dixon-Coles, plus pre-match odds where available",
             "ensemble_stats": "Elo + Dixon-Coles, no odds", "base_rate": "league averages, ignores teams"}
    test = {k: scored(period(v[v.league != CL], *TEST)) for k, v in preds.items()}
    mkt = market(test["ensemble"])
    pre = market_pre(test["ensemble"])
    n = len(mkt)
    share = float(test["ensemble"].used_market.mean())
    print(f"\nTest: {TEST[0]:%Y-%m-%d} to {TEST[1]:%Y-%m-%d}, {n:,} matches with Pinnacle closing odds "
          f"({share:.0%} with pre-match odds)\n")
    print("| Model | Log loss | Brier | RPS | Accuracy | Notes |\n|---|---|---|---|---|---|")
    board = []
    for k in labels:
        sc = score_frame(test[k])
        board.append(_row(k, labels[k], sc, notes.get(k, "")))
        print(_fmt(labels[k], sc, notes.get(k, "")))
    sc = score_frame(pre)
    board.append(_row("market_pre", "Market, pre-match average", sc, f"only the {len(pre):,} matches with pre-match odds"))
    print(_fmt("market, pre-match average", sc, f"{len(pre):,} matches"))
    sc = score_frame(mkt)
    board.append(_row("market", "Market (Pinnacle closing)", sc, "benchmark only"))
    print(_fmt("market (Pinnacle closing)", sc, "benchmark only"))
    with_odds = test["ensemble"][test["ensemble"].used_market]
    odds_rows = {"matches": len(with_odds), "xgenius": round(score_frame(with_odds)["log_loss"], 4),
                 "market_pre": round(score_frame(market_pre(with_odds))["log_loss"], 4),
                 "market_close": round(score_frame(market(with_odds))["log_loss"], 4)}
    print(f"\nOn the {len(with_odds):,} matches with pre-match odds: xGenius {odds_rows['xgenius']:.4f}, "
          f"pre-match odds {odds_rows['market_pre']:.4f}, Pinnacle closing {odds_rows['market_close']:.4f}")

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
    season_board = [_row(k, labels[k], score_frame(season[k])) for k in ("ensemble", "ensemble_stats", "base_rate")
                    if len(season[k])]
    if season_board:
        print(f"\nThis season so far ({len(season['ensemble'])} shown matches): "
              f"xGenius log loss {season_board[0]['log_loss']:.4f}, accuracy {season_board[0]['accuracy']:.1%}")

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    perf = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "test": {"from": f"{TEST[0]:%Y-%m-%d}", "to": f"{TEST[1]:%Y-%m-%d}", "matches": n,
                 "leagues": int(mkt.league.nunique()), "share_with_odds": round(share, 3),
                 "leaderboard": board, "with_odds": odds_rows,
                 "by_league": [{"league": lg, **{k: round(float(v), 4) for k, v in row.items()}}
                               for lg, row in by_league.iterrows()],
                 "calibration": calibration(test["ensemble"])},
        "champions_league": {"from": f"{CL_SCORED_FROM:%Y-%m-%d}", "to": f"{TEST[1]:%Y-%m-%d}",
                             "matches": len(cl["ensemble"]), "leaderboard": cl_board},
        "season": {"from": f"{TEST[1]:%Y-%m-%d}", "to": f"{end:%Y-%m-%d}",
                   "matches": len(season["ensemble"]), "leaderboard": season_board},
    }
    (WEB_DATA / "performance.json").write_text(json.dumps(perf, indent=1))
    print(f"\nwrote {WEB_DATA / 'performance.json'} and {PARAMS_PATH}")


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
    else:
        run()
