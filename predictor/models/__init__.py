"""Every model follows the same three-call contract so the backtest can treat
them alike and never leak the future:

    fit(history)       learn from matches strictly before the test period
    predict(matches)   (n, 3) array of P(home), P(draw), P(away); must not read goals
    update(played)     absorb results once they're known (online models update,
                       batch models may refit)
"""
import numpy as np
import pandas as pd

from predictor.metrics import outcome


class Model:
    name = "model"

    def fit(self, history: pd.DataFrame) -> None:
        raise NotImplementedError

    def predict(self, matches: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError

    def update(self, played: pd.DataFrame) -> None:
        raise NotImplementedError


class BaseRate(Model):
    """Each league's historical H/D/A frequencies, ignoring who's playing.
    The floor: any real model must beat this."""
    name = "base_rate"

    def fit(self, history):
        self.counts = {}
        self.update(history)

    def update(self, played):
        y = outcome(played.home_goals, played.away_goals)
        for league, res in zip(played.league, y):
            self.counts.setdefault(league, np.ones(3))[res] += 1  # +1 smoothing

    def predict(self, matches):
        default = np.array([0.45, 0.27, 0.28])
        return np.array([self.counts[lg] / self.counts[lg].sum() if lg in self.counts else default
                         for lg in matches.league])
