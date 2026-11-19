import datetime as dt

import numpy as np
import pandas as pd
import pytest

from predictor import metrics
from predictor.backtest import walk_forward
from predictor.models import BaseRate, Model
from predictor.models.elo import Elo, fit_ordered_logit, ordered_logit_probs


# --- metrics ----------------------------------------------------------------
def test_perfect_and_uniform_forecasts():
    y = np.array([0, 1, 2])
    perfect = np.eye(3)
    assert metrics.log_loss(perfect, y) == pytest.approx(0, abs=1e-9)
    assert metrics.brier(perfect, y) == 0 and metrics.rps(perfect, y) == 0
    uniform = np.full((3, 3), 1 / 3)
    assert metrics.log_loss(uniform, y) == pytest.approx(np.log(3))
    assert metrics.brier(uniform, y) == pytest.approx(2 / 3)


def test_rps_prefers_near_misses():
    # Home won; predicting a draw is less wrong than predicting an away win
    y = np.array([0])
    assert metrics.rps([[0, 1, 0]], y) < metrics.rps([[0, 0, 1]], y)


def test_implied_probs_remove_margin():
    p = metrics.implied_probs([1.9], [3.5], [4.2])
    assert p.sum() == pytest.approx(1)
    assert p[0, 0] > p[0, 2] > 0


# --- ordered logit --------------------------------------------------------------
def test_ordered_logit_is_valid_and_monotone():
    p = ordered_logit_probs(np.linspace(-2, 2, 9), (2.0, -1.0, 0.0))
    assert np.allclose(p.sum(axis=1), 1) and (p > 0).all()
    assert (np.diff(p[:, 0]) > 0).all() and (np.diff(p[:, 2]) < 0).all()


def test_ordered_logit_recovers_parameters():
    rng = np.random.default_rng(0)
    true = np.array([2.5, -0.8, 0.2])
    x = rng.normal(0, 0.5, 20000)
    p = ordered_logit_probs(x, true)
    y = np.array([rng.choice(3, p=row) for row in p])
    assert np.allclose(fit_ordered_logit(x, y), true, atol=0.1)


# --- Elo ----------------------------------------------------------------------
def _season(teams, strengths, season, start, rng):
    rows, date = [], pd.Timestamp(start)
    for h in teams:
        for a in teams:
            if h != a:
                lam_h = np.exp(0.2 + strengths[h] - strengths[a])
                lam_a = np.exp(strengths[a] - strengths[h])
                rows.append(dict(date=date, season=season, league="test", home_id=h, away_id=a,
                                 home_goals=rng.poisson(lam_h), away_goals=rng.poisson(lam_a)))
                date += dt.timedelta(days=1)
    return rows


def _synthetic(seasons=4):
    rng = np.random.default_rng(1)
    teams = list("ABCDEFGH")
    strengths = dict(zip(teams, np.linspace(0.6, -0.6, 8)))
    rows = []
    for s in range(seasons):
        rows += _season(teams, strengths, 2014 + s, f"{2014 + s}-08-01", rng)
    return pd.DataFrame(rows)


def test_elo_ranks_teams_by_true_strength():
    m = Elo()
    m.fit(_synthetic())
    r = m.ratings()
    assert r.index[0] == "A" and r.index[-1] == "H"


def test_elo_favours_stronger_team_and_home():
    m = Elo()
    m.fit(_synthetic())
    fx = pd.DataFrame(dict(date=[pd.Timestamp("2017-10-15")] * 2, season=2017, league="test",
                           home_id=["A", "H"], away_id=["H", "A"]))
    p = m.predict(fx)
    assert p[0, 0] > 0.6 and p[1, 2] > 0.4
    assert p[0, 0] > p[1, 2]  # home advantage


def test_returning_team_restarts_below_league_mean():
    m = Elo(promoted_gap=100)
    df = _synthetic(2)
    m.fit(df[df.home_id != "Z"])
    mean = m._league_mean("test", pd.Timestamp("2016-08-01"))
    m._prepare("Z", "test", 2016, pd.Timestamp("2016-08-01"))
    assert m.rating["Z"] == pytest.approx(mean - 100)


# --- harness ------------------------------------------------------------------
class Spy(Model):
    """Fails if predict() can see goals or if update() reveals a day early."""
    name = "spy"

    def fit(self, history):
        self.seen_until = history.date.max()

    def predict(self, matches):
        assert "home_goals" not in matches and "away_goals" not in matches
        assert (matches.date > self.seen_until).all()
        return np.full((len(matches), 3), 1 / 3)

    def update(self, played):
        self.seen_until = played.date.max()


def test_walk_forward_never_leaks():
    df = _synthetic()
    preds = walk_forward(Spy(), df, pd.Timestamp("2016-08-01"), pd.Timestamp("2018-07-01"))
    assert len(preds) == (df.date >= "2016-08-01").sum()


def test_base_rate_is_league_frequency():
    df = pd.DataFrame(dict(league="x", home_goals=[1, 1, 0, 0], away_goals=[0, 0, 0, 1]))
    m = BaseRate()
    m.fit(df)
    assert m.predict(df.head(1))[0] == pytest.approx(np.array([3, 2, 2]) / 7)
