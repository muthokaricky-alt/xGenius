import numpy as np
import pandas as pd
import pytest

from predictor.races import clean_sheet_race, player_race, simulate


def test_simulate_top_chances_sum_to_one_and_split_ties():
    rng = np.random.default_rng(0)
    out = simulate(np.array([10.0, 10.0]), np.zeros((1000, 2)))
    assert out["p_top"] == pytest.approx([0.5, 0.5])
    out = simulate(np.array([5.0, 3.0, 1.0]), rng.poisson([2.0, 4.0, 1.0], (5000, 3)))
    assert out["p_top"].sum() == pytest.approx(1)
    assert out["lo"][0] <= out["mean"][0] <= out["hi"][0]


def test_player_race_scales_with_share_and_team_outlook():
    rng = np.random.default_rng(1)
    scorers = pd.DataFrame(dict(league="x", player=["Star", "Bench"], team_id=["a", "a"],
                                goals=[10, 1], assists=[0, 0], played=[10, 4]))
    so_far = pd.DataFrame(dict(league="x", team_id=["a"], played=[10], gf=[20], cs=[3]))
    outlook = pd.DataFrame(dict(league="x", team_id=["a"] * 20, xg=[2.0] * 20, p_cs=[0.3] * 20))
    r = player_race(scorers, so_far, outlook, "goals", rng).set_index("player")
    assert r.future["Star"] == pytest.approx(10 / 23 * 40)
    assert r.projected["Star"] > r.projected["Bench"] and r.p_top["Star"] > 0.99
    assert player_race(scorers, so_far, outlook, "assists", rng).empty  # nobody has assists


def test_clean_sheet_race_adds_expected_clean_sheets():
    rng = np.random.default_rng(2)
    so_far = pd.DataFrame(dict(league="x", team_id=["a", "b"], played=[10, 10], gf=[15, 12], cs=[4, 2]))
    outlook = pd.DataFrame(dict(league="x", team_id=["a"] * 10 + ["b"] * 10, xg=1.5,
                                p_cs=[0.5] * 10 + [0.1] * 10))
    r = clean_sheet_race(so_far, outlook, rng).set_index("team_id")
    assert r.projected["a"] == pytest.approx(9, abs=0.15)
    assert r.projected["b"] == pytest.approx(3, abs=0.15)
    assert r.remaining["a"] == 10 and r.p_top["a"] > 0.95
