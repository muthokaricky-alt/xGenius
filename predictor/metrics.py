"""Scoring rules for 1X2 probabilities. Columns are always (home, draw, away);
outcomes are 0 = home win, 1 = draw, 2 = away win. Lower is better for all
except accuracy.

log loss  the leaderboard metric: punishes confident mistakes hardest
Brier     squared error summed over the three outcomes (0..2)
RPS       ranked probability score: treats H > D > A as ordered, so calling a
          draw when the home side wins is less wrong than calling an away win
"""
import numpy as np
import pandas as pd

EPS = 1e-15


def outcome(home_goals, away_goals) -> np.ndarray:
    hg, ag = np.asarray(home_goals), np.asarray(away_goals)
    return np.where(hg > ag, 0, np.where(hg == ag, 1, 2))


def _onehot(y) -> np.ndarray:
    return np.eye(3)[np.asarray(y)]


def log_loss(p, y) -> float:
    p = np.asarray(p, float)
    return float(-np.mean(np.log(np.clip(p[np.arange(len(p)), y], EPS, 1))))


def brier(p, y) -> float:
    return float(np.mean(np.sum((np.asarray(p, float) - _onehot(y)) ** 2, axis=1)))


def rps(p, y) -> float:
    cp, co = np.cumsum(np.asarray(p, float), axis=1), np.cumsum(_onehot(y), axis=1)
    return float(np.mean(np.sum((cp[:, :2] - co[:, :2]) ** 2, axis=1) / 2))


def accuracy(p, y) -> float:
    return float(np.mean(np.argmax(np.asarray(p), axis=1) == np.asarray(y)))


def score(p, y) -> dict:
    return {"log_loss": log_loss(p, y), "brier": brier(p, y), "rps": rps(p, y),
            "accuracy": accuracy(p, y), "n": len(y)}


def implied_probs(odds_h, odds_d, odds_a) -> np.ndarray:
    """Bookmaker odds -> probabilities, removing the margin proportionally."""
    inv = 1 / np.column_stack([odds_h, odds_d, odds_a]).astype(float)
    return inv / inv.sum(axis=1, keepdims=True)


def score_frame(df: pd.DataFrame, cols=("p_home", "p_draw", "p_away")) -> dict:
    return score(df[list(cols)].to_numpy(), outcome(df.home_goals, df.away_goals))
