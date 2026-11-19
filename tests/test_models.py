import datetime as dt

import numpy as np
import pandas as pd
import pytest

from predictor.models.dixon_coles import DixonColes, outcome_probs, score_matrix
from predictor.models.ensemble import fit_pool, pool

ENG = ["arsenal", "chelsea", "everton", "fulham"]
NED = ["ajax", "psv", "feyenoord", "utrecht"]


def _league(teams, league, strength, start, rng, rounds=6):
    rows, date = [], dt.datetime.fromisoformat(start)
    for _ in range(rounds):
        for h in teams:
            for a in teams:
                if h != a:
                    lh = np.exp(0.45 + strength[h] - strength[a])
                    la = np.exp(0.25 + strength[a] - strength[h])
                    rows.append(dict(date=date, season=date.year, league=league, home_id=h, away_id=a,
                                     home_goals=rng.poisson(lh), away_goals=rng.poisson(la), neutral=False))
                    date += dt.timedelta(days=1)
    return rows


def _data():
    rng = np.random.default_rng(0)
    s = {**dict(zip(ENG, [0.5, 0.2, -0.2, -0.5])), **dict(zip(NED, [0.5, 0.2, -0.2, -0.5]))}
    rows = _league(ENG, "premier_league", s, "2024-08-01", rng) + _league(NED, "eredivisie", s, "2024-08-01", rng)
    # Champions League: English sides are 0.4 log-goals stronger than their Dutch counterparts
    date = dt.datetime(2024, 9, 1)
    for _ in range(15):
        for e, n in zip(ENG, NED):
            for h, a, dh, da in ((e, n, 0.4, 0.0), (n, e, 0.0, 0.4)):
                rows.append(dict(date=date, season=2024, league="champions_league", home_id=h, away_id=a,
                                 home_goals=rng.poisson(np.exp(0.45 + s[h] + dh - s[a] - da)),
                                 away_goals=rng.poisson(np.exp(0.25 + s[a] + da - s[h] - dh)), neutral=False))
                date += dt.timedelta(days=1)
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def test_score_matrix_is_a_distribution():
    m = score_matrix(1.6, 1.1, -0.05)
    assert m.sum() == pytest.approx(1) and (m >= 0).all()
    p = outcome_probs(m)
    assert p.sum() == pytest.approx(1) and p[0] > p[2]


def test_dixon_coles_orders_teams_and_links_leagues():
    m = DixonColes()
    m.fit(_data())
    r = m.ratings().set_index("team_id").rating
    assert r["arsenal"] > r["chelsea"] > r["everton"] > r["fulham"]
    # same domestic strength, but CL results say England is the stronger league
    assert r["arsenal"] > r["ajax"] and r["fulham"] > r["utrecht"]
    assert m.p["home"]["premier_league"] > 0


def test_dixon_coles_unknown_team_gets_promoted_prior():
    m = DixonColes()
    m.fit(_data())
    fx = pd.DataFrame(dict(date=[pd.Timestamp("2025-06-01")], season=2025, league="premier_league",
                           home_id=["arsenal"], away_id=["brand-new-fc"], neutral=False))
    p = m.predict(fx)[0]
    assert p[0] > 0.5 and m.experience("brand-new-fc") == 0


def test_pool_weights_and_cl_fallback():
    pe = np.array([[0.6, 0.25, 0.15]] * 2)
    pd_ = np.array([[0.4, 0.3, 0.3]] * 2)
    out = pool(pe, pd_, [1.0, 0.0, 0.0, 0.0], is_cl=[False, True])
    assert out[0] == pytest.approx(pe[0])            # domestic: Elo only
    assert out[1] == pytest.approx(pd_[1])           # CL: Elo ignored, DC gets its weight


def test_fit_pool_prefers_the_informative_model():
    rng = np.random.default_rng(3)
    truth = rng.dirichlet([4, 2, 2], 4000)
    y = np.array([rng.choice(3, p=t) for t in truth])
    noise = np.full_like(truth, 1 / 3)
    w_good, w_noise, *_ = fit_pool(truth, noise, y)
    assert w_good > 0.8
