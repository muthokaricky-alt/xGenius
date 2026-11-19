"""Elo baseline.

Ratings
  - Update after each match: delta = K * g(goal diff) * (result - expected),
    with g = 1, 1.5, then (11 + gd) / 8 (as used by World Football Elo).
  - Home advantage HOME_ADV is added to the home side's rating before computing
    the expected result.
  - At a team's first match of a new season its rating is pulled toward its
    league's mean by REGRESS (summer transfers, managers, etc.).
  - A team we haven't seen for ABSENT_DAYS (new, or back after relegation)
    starts PROMOTED_GAP points below its league's mean.

Ratings are per league: no domestic match links two leagues, so a 1600 in
Austria isn't comparable to a 1600 in England. Cross-league strength is
milestone 7.

Probabilities
  Elo only gives an expected score, not a draw probability. We map the rating
  gap x = (home + HOME_ADV - away) / 400 to H/D/A with an ordered logit
  (two cut-points, so draws are most likely when teams are level), fitted by
  maximum likelihood on past pre-match gaps only. It's refitted every
  REFIT_DAYS during the backtest.
"""
import datetime as dt

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

from predictor.metrics import outcome
from predictor.models import Model


def ordered_logit_probs(x, params) -> np.ndarray:
    slope, c1, log_gap = params
    z = slope * np.asarray(x, float)
    c2 = c1 + np.exp(log_gap)
    p_away = expit(c1 - z)
    p_not_home = expit(c2 - z)
    return np.column_stack([1 - p_not_home, p_not_home - p_away, p_away])


def fit_ordered_logit(x, y, start=(2.0, -1.0, 0.0)) -> np.ndarray:
    x, y = np.asarray(x, float), np.asarray(y)

    def nll(params):
        p = ordered_logit_probs(x, params)
        return -np.sum(np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1)))

    return minimize(nll, np.asarray(start, float), method="Nelder-Mead",
                    options={"xatol": 1e-4, "fatol": 1e-3, "maxiter": 2000}).x


class Elo(Model):
    name = "elo"
    # Tuned on 2016/17-2017/18 (validation), never on the test seasons.
    # See `python -m predictor.backtest --tune`. home_adv barely matters (0/20/40
    # within 0.0002 log loss): the ordered logit's cut-points already learn the
    # home edge, so it only affects rating updates, and those even out over a
    # season of half home, half away games.
    DEFAULTS = dict(k=12.0, home_adv=0.0, regress=0.1, promoted_gap=50.0)
    ABSENT_DAYS = 250   # longer than any summer/winter break
    REFIT_DAYS = 30
    BURN_IN_DAYS = 365  # ratings are meaningless at first; don't calibrate on them

    def __init__(self, **params):
        p = {**self.DEFAULTS, **params}
        self.k, self.home_adv = p["k"], p["home_adv"]
        self.regress, self.promoted_gap = p["regress"], p["promoted_gap"]

    # --- rating state -------------------------------------------------------
    def _reset(self):
        self.rating = {}     # team_id -> rating
        self.last_seen = {}  # team_id -> (date, season, league)
        self.calib_x, self.calib_y, self.calib_date = [], [], []
        self.params = np.array([2.0, -1.0, 0.0])
        self.first_date = None
        self.last_refit = None

    def _league_mean(self, league, date):
        cutoff = date - dt.timedelta(days=self.ABSENT_DAYS)
        rs = [self.rating[t] for t, (d, _, lg) in self.last_seen.items() if lg == league and d >= cutoff]
        return float(np.mean(rs)) if rs else 1500.0

    def _prepare(self, team, league, season, date):
        """Season regression / new-team init. Uses only the past, so it's safe
        to run before predicting."""
        seen = self.last_seen.get(team)
        if seen is None or (date - seen[0]).days > self.ABSENT_DAYS or seen[2] != league:
            self.rating[team] = self._league_mean(league, date) - self.promoted_gap
        elif seen[1] != season:
            mean = self._league_mean(league, date)
            self.rating[team] = mean + (1 - self.regress) * (self.rating[team] - mean)
        else:
            return
        self.last_seen[team] = (date, season, league)

    def _gap(self, row):
        for team in (row.home_id, row.away_id):
            self._prepare(team, row.league, row.season, row.date)
        return (self.rating[row.home_id] + self.home_adv - self.rating[row.away_id]) / 400

    def _play(self, row):
        x = self._gap(row)
        expected = 1 / (1 + 10 ** (-x))
        gd = row.home_goals - row.away_goals
        result = 1.0 if gd > 0 else 0.5 if gd == 0 else 0.0
        g = 1.0 if abs(gd) <= 1 else 1.5 if abs(gd) == 2 else (11 + abs(gd)) / 8
        delta = self.k * g * (result - expected)
        self.rating[row.home_id] += delta
        self.rating[row.away_id] -= delta
        for team in (row.home_id, row.away_id):
            self.last_seen[team] = (row.date, row.season, row.league)
        self.calib_x.append(x)
        self.calib_y.append(int(outcome(row.home_goals, row.away_goals)))
        self.calib_date.append(row.date)

    def _refit(self, now):
        burn = self.first_date + dt.timedelta(days=self.BURN_IN_DAYS)
        keep = np.array(self.calib_date) >= burn
        if keep.sum() > 500:
            self.params = fit_ordered_logit(np.array(self.calib_x)[keep],
                                            np.array(self.calib_y)[keep], self.params)
        self.last_refit = now

    # --- Model contract -----------------------------------------------------
    def fit(self, history):
        self._reset()
        history = history.sort_values("date")
        self.first_date = history.date.min()
        for row in history.itertuples(index=False):
            self._play(row)
        self._refit(history.date.max())

    def update(self, played):
        for row in played.sort_values("date").itertuples(index=False):
            self._play(row)
        now = played.date.max()
        if (now - self.last_refit).days >= self.REFIT_DAYS:
            self._refit(now)

    def predict(self, matches):
        x = [self._gap(row) for row in matches.itertuples(index=False)]
        return ordered_logit_probs(x, self.params)

    def ratings(self) -> pd.Series:
        return pd.Series(self.rating).sort_values(ascending=False)
