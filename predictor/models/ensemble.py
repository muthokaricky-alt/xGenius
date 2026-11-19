"""Ensemble of Elo, Dixon-Coles and (when available) the betting market,
calibrated (milestone 6, revised).

Two logarithmic pools, each with per-outcome biases (b_home = 0):

  stats   p ∝ p_elo^w_elo · p_dc^w_dc · exp(b), plus its own draw/away
          biases for the Champions League. In the CL, Elo ratings from
          different leagues aren't comparable, so Dixon-Coles carries both
          weights there.
  market  p ∝ p_elo^w_elo · p_dc^w_dc · p_mkt^w_mkt · exp(b), used whenever
          pre-match market-average odds exist (margin removed proportionally).

Both are refitted by maximum likelihood on out-of-sample walk-forward
predictions only: for the backtest, every test season is scored with pools
fitted on the seasons before it; for live forecasts, on everything up to the
current season (`python -m predictor.backtest --fit-ensemble`).

Gradient boosting (the original milestone 6 plan) wasn't pursued: with only
model outputs and odds as inputs there's nothing for trees to find that the
pools can't, and features that could help (lineups, injuries) aren't in our data.
"""
import json

import numpy as np
from scipy.optimize import minimize

from predictor.config import ROOT
from predictor.metrics import implied_probs

PARAMS_PATH = ROOT / "config" / "ensemble.json"
STATS0 = [0.5, 0.5, 0.0, 0.0, 0.0, 0.0]       # w_elo, w_dc, b_draw, b_away, cl_b_draw, cl_b_away
MARKET0 = [0.2, 0.2, 0.6, 0.0, 0.0]           # w_elo, w_dc, w_mkt, b_draw, b_away


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _log(p):
    return np.log(np.clip(np.asarray(p, float), 1e-9, 1))


def pool_stats(p_elo, p_dc, params, is_cl=None):
    w_elo, w_dc, b_draw, b_away, cl_draw, cl_away = params
    n = len(p_dc)
    is_cl = np.zeros(n, bool) if is_cl is None else np.asarray(is_cl, bool)
    we = np.where(is_cl, 0.0, w_elo)
    wd = np.where(is_cl, w_dc + w_elo, w_dc)
    z = we[:, None] * _log(p_elo) + wd[:, None] * _log(p_dc)
    z[:, 1] += b_draw + np.where(is_cl, cl_draw, 0.0)
    z[:, 2] += b_away + np.where(is_cl, cl_away, 0.0)
    return _softmax(z)


def pool_market(p_elo, p_dc, p_mkt, params):
    w_elo, w_dc, w_mkt, b_draw, b_away = params
    z = w_elo * _log(p_elo) + w_dc * _log(p_dc) + w_mkt * _log(p_mkt)
    z[:, 1] += b_draw
    z[:, 2] += b_away
    return _softmax(z)


def market_probs(odds) -> tuple[np.ndarray, np.ndarray]:
    """(n, 3) decimal odds (NaN where missing) -> probabilities and a has-odds mask."""
    odds = np.asarray(odds, float)
    ok = np.isfinite(odds).all(axis=1) & (odds > 1).all(axis=1)
    p = np.full(odds.shape, np.nan)
    if ok.any():
        p[ok] = implied_probs(odds[ok, 0], odds[ok, 1], odds[ok, 2])
    return p, ok


def combine(p_elo, p_dc, odds, is_cl, params) -> tuple[np.ndarray, np.ndarray]:
    """Final forecast: the market pool where odds exist, else the stats pool.
    Returns (probabilities, used_market mask)."""
    p = pool_stats(p_elo, p_dc, params["stats"], is_cl)
    p_mkt, ok = market_probs(odds)
    ok = ok & ~np.asarray(is_cl, bool)
    if ok.any():
        p[ok] = pool_market(np.asarray(p_elo)[ok], np.asarray(p_dc)[ok], p_mkt[ok], params["market"])
    return p, ok


def _fit(fn, x0, args, y):
    y = np.asarray(y)
    n = len(y)

    def nll(t):
        return -np.mean(np.log(np.clip(fn(*args, t)[np.arange(n), y], 1e-12, 1)))

    return [float(v) for v in minimize(nll, x0, method="L-BFGS-B").x]


def fit_params(p_elo, p_dc, odds, is_cl, y) -> dict:
    p_elo, p_dc, y = np.asarray(p_elo), np.asarray(p_dc), np.asarray(y)
    stats = _fit(lambda e, d, c, t: pool_stats(e, d, t, c), STATS0, (p_elo, p_dc, is_cl), y)
    p_mkt, ok = market_probs(odds)
    ok = ok & ~np.asarray(is_cl, bool)
    market = (_fit(lambda e, d, m, t: pool_market(e, d, m, t), MARKET0, (p_elo[ok], p_dc[ok], p_mkt[ok]), y[ok])
              if ok.sum() > 1000 else MARKET0)
    return {"stats": stats, "market": market}


def load_params() -> dict:
    if PARAMS_PATH.exists():
        data = json.loads(PARAMS_PATH.read_text())
        if "stats" in data:
            return {"stats": data["stats"], "market": data["market"]}
    return {"stats": STATS0, "market": MARKET0}
