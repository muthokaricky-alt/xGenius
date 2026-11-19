"""Ensemble of Elo and Dixon-Coles, calibrated (milestone 6).

Logarithmic pooling:
    p(k) ∝ p_elo(k) ** w_elo * p_dc(k) ** w_dc * exp(b_k),   b_home = 0

Four parameters, fitted by maximum likelihood on the validation seasons'
walk-forward predictions (never the test seasons). Weights above/below 1
sharpen/flatten the forecasts and b_draw / b_away fix any bias in the draw
and away-win rates, so this is also the calibration step.

Champions League: Elo ratings from different leagues aren't comparable, so the
pool there is Dixon-Coles alone (with the same calibration biases).

Gradient boosting (the original milestone 6 plan) wasn't pursued: with only
the two models' outputs as inputs there's nothing for trees to find that the
pool can't, and features that could help (lineups, injuries) aren't in our data.
"""
import json

import numpy as np
from scipy.optimize import minimize

from predictor.config import ROOT
from predictor.data import CL
from predictor.models import Model
from predictor.models.dixon_coles import DixonColes
from predictor.models.elo import Elo

PARAMS_PATH = ROOT / "config" / "ensemble.json"


def pool(p_elo, p_dc, params, is_cl=None):
    w_elo, w_dc, b_draw, b_away = params
    p_elo, p_dc = np.clip(np.asarray(p_elo), 1e-9, 1), np.clip(np.asarray(p_dc), 1e-9, 1)
    is_cl = np.zeros(len(p_dc), bool) if is_cl is None else np.asarray(is_cl, bool)
    we = np.where(is_cl, 0.0, w_elo)           # CL: Dixon-Coles carries the full weight
    wd = np.where(is_cl, w_dc + w_elo, w_dc)
    z = we[:, None] * np.log(p_elo) + wd[:, None] * np.log(p_dc) + np.array([0, b_draw, b_away])
    z -= z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def fit_pool(p_elo, p_dc, y) -> list[float]:
    y = np.asarray(y)

    def nll(params):
        p = pool(p_elo, p_dc, params)
        return -np.mean(np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1)))

    return list(minimize(nll, [0.5, 0.5, 0.0, 0.0], method="Nelder-Mead",
                         options={"xatol": 1e-5, "fatol": 1e-7, "maxiter": 4000}).x)


def load_params() -> list[float]:
    if PARAMS_PATH.exists():
        return json.loads(PARAMS_PATH.read_text())["params"]
    return [0.5, 0.5, 0.0, 0.0]


class Ensemble(Model):
    name = "ensemble"

    def __init__(self, params=None):
        self.elo, self.dc = Elo(), DixonColes()
        self.params = params or load_params()

    def fit(self, history):
        self.elo.fit(history)
        self.dc.fit(history)

    def update(self, played):
        self.elo.update(played)
        self.dc.update(played)

    def predict(self, matches):
        return pool(self.elo.predict(matches), self.dc.predict(matches), self.params,
                    matches.league.eq(CL).to_numpy())
