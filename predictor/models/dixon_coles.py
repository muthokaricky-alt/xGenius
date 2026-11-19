"""Dixon-Coles Poisson model, fitted jointly on every league plus the
Champions League.

Goals
  home goals ~ Poisson(lam), away goals ~ Poisson(mu), with
    log lam = base[c] + home[c] + att[i] - def[j]
    log mu  = base[c]           + att[j] - def[i]
  c is the competition (each league, and the CL), i/j the home/away team.
  The Dixon-Coles factor tau(rho) then corrects the four low scores
  (0-0, 1-0, 0-1, 1-1), which independent Poissons get slightly wrong.

Cross-league strength (milestone 7)
  att[i] = A[g] + a[i] and def[i] = D[g] + d[i], where g is the team's
  country. Domestic matches only see a[i], d[i] (A and D cancel against the
  league's base rate); Champions League matches are what pin down A and D,
  i.e. how strong each league is relative to the others. Clubs from
  countries we don't ingest (Slavia, Qarabag...) share one group, "other",
  so they borrow strength from each other and from every CL match they play.

Regularisation
  a, d are shrunk toward a prior (0 = league average; promoted teams start at
  -PROMOTED below it) with weight TEAM_RIDGE, measured in "matches": a team
  with fewer weighted matches than that leans mostly on the prior.

Time
  A match played t days before the fit counts with weight 0.5 ** (t / HALF_LIFE).
  We refit every REFIT_DAYS; between refits predictions use the last fit.
"""
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.stats import poisson

from predictor.data import CL
from predictor.leagues import LEAGUES
from predictor.models import Model
from predictor.teams import load_teams

LEAGUE_COUNTRIES = {m["country"] for m in LEAGUES.values() if m["country"]}
MAX_GOALS = 10

# Goal-count calibration. Above ~2 expected goals the Poisson rates run high:
# in the 2018-2026 walk-forward, sides predicted 3.5+ scored ~12% fewer goals
# than forecast (dominant teams ease off once ahead). Rates above GOAL_KNEE grow
# at GOAL_SLOPE instead of 1. Fitted by maximum Poisson likelihood on 2018-07 to
# 2023-06; on 2023-07 to 2026-06 it lifts goal-count likelihood (-0.84866 ->
# -0.84847), exact-score log loss in big-favourite matches (3.0439 -> 3.0373)
# and fixes the top bins (3.0-3.5: 3.20 -> 2.93 vs 2.97 actual), at a cost of
# +0.0003 over-2.5 log loss. Applied to goal outputs (xG, score grid, goal
# markets, season races), not to the 1X2 forecast, which was already calibrated.
GOAL_KNEE = 2.0
GOAL_SLOPE = 0.777


def calibrate_rate(rate):
    rate = np.asarray(rate, float)
    return np.where(rate <= GOAL_KNEE, rate, GOAL_KNEE + GOAL_SLOPE * (rate - GOAL_KNEE))


@lru_cache(maxsize=None)
def team_group(team_id: str) -> str:
    teams, _ = load_teams()
    country = teams.get(team_id, {}).get("country")
    return country if country in LEAGUE_COUNTRIES else "other"


def tau_matrix(lam: float, mu: float, rho: float, n: int = MAX_GOALS + 1) -> np.ndarray:
    t = np.ones((n, n))
    t[0, 0] = 1 - lam * mu * rho
    t[0, 1] = 1 + lam * rho
    t[1, 0] = 1 + mu * rho
    t[1, 1] = 1 - rho
    return t


def score_matrix(lam: float, mu: float, rho: float) -> np.ndarray:
    """P(home = x, away = y) for x, y in 0..MAX_GOALS, rows = home goals."""
    g = np.arange(MAX_GOALS + 1)
    m = np.outer(poisson.pmf(g, lam), poisson.pmf(g, mu)) * tau_matrix(lam, mu, rho)
    m = np.clip(m, 0, None)
    return m / m.sum()


def outcome_probs(m: np.ndarray) -> np.ndarray:
    return np.array([np.tril(m, -1).sum(), np.trace(m), np.triu(m, 1).sum()])


class DixonColes(Model):
    name = "dixon_coles"
    # Tuned on 2016/17-2017/18 (validation); see `python -m predictor.backtest --tune-dc`.
    DEFAULTS = dict(half_life=300.0, team_ridge=2.0, promoted=0.1, group_ridge=10.0, xg_weight=0.5)
    REFIT_DAYS = 7
    WINDOW = 4  # half-lives of history used (older matches weigh < 6%)

    def __init__(self, **params):
        p = {**self.DEFAULTS, **params}
        self.half_life, self.team_ridge, self.promoted = p["half_life"], p["team_ridge"], p["promoted"]
        self.group_ridge, self.xg_weight = p["group_ridge"], p["xg_weight"]
        self.p = None  # fitted parameters (dict of name -> value maps)

    # --- fitting ------------------------------------------------------------
    def _promoted_teams(self, df) -> set:
        """Teams playing this season in a league they weren't in last season."""
        out = set()
        for league, g in df[df.league != CL].groupby("league"):
            seasons = sorted(g.season.unique())
            if len(seasons) < 2:
                continue
            cur, prev = (g[g.season == s] for s in seasons[-2:][::-1])
            out |= (set(cur.home_id) | set(cur.away_id)) - (set(prev.home_id) | set(prev.away_id))
        return out

    def _refit(self, now):
        df = pd.concat(self._chunks, ignore_index=True) if len(self._chunks) > 1 else self._chunks[0]
        self._chunks = [df]
        age = (now - df.date).dt.days.to_numpy()
        keep = age <= self.WINDOW * self.half_life
        df, age = df[keep], age[keep]
        w = 0.5 ** (age / self.half_life)

        teams = pd.Index(sorted(set(df.home_id) | set(df.away_id)))
        comps = pd.Index(sorted(df.league.unique()))
        groups = pd.Index(sorted({team_group(t) for t in teams}))
        T, C, G = len(teams), len(comps), len(groups)
        hi, ai = teams.get_indexer(df.home_id), teams.get_indexer(df.away_id)
        ci = comps.get_indexer(df.league)
        tg = groups.get_indexer([team_group(t) for t in teams])
        hg, ag = tg[hi], tg[ai]
        home_on = (~df.neutral.astype(bool)).to_numpy().astype(float)
        yh, ya = df.home_goals.to_numpy(float), df.away_goals.to_numpy(float)
        if self.xg_weight and "home_xg" in df:  # milestone 5: blend in xG where we have it
            has = df.home_xg.notna().to_numpy()
            wx = self.xg_weight
            yh = np.where(has, (1 - wx) * yh + wx * df.home_xg.to_numpy(float), yh)
            ya = np.where(has, (1 - wx) * ya + wx * df.away_xg.to_numpy(float), ya)
        goals_h, goals_a = df.home_goals.to_numpy(float), df.away_goals.to_numpy(float)

        promoted = self._promoted_teams(df)
        prior = np.array([-self.promoted if t in promoted else 0.0 for t in teams])
        lt, lg = self.team_ridge, self.group_ridge
        sl = np.cumsum([0, C, C, G, G, T, T])

        def unpack(x):
            return [x[sl[k]:sl[k + 1]] for k in range(6)]

        def f(x):
            base, home, A, D, a, d = unpack(x)
            eh = base[ci] + home[ci] * home_on + A[hg] + a[hi] - D[ag] - d[ai]
            ea = base[ci] + A[ag] + a[ai] - D[hg] - d[hi]
            lh, la = np.exp(eh), np.exp(ea)
            nll = -np.sum(w * (yh * eh - lh + ya * ea - la))
            nll += lt * (np.sum((a - prior) ** 2) + np.sum((d - prior) ** 2)) + lg * (A @ A + D @ D)
            rh, ra = w * (lh - yh), w * (la - ya)
            g = np.concatenate([
                np.bincount(ci, rh + ra, C),
                np.bincount(ci, rh * home_on, C),
                np.bincount(hg, rh, G) + np.bincount(ag, ra, G) + 2 * lg * A,
                -np.bincount(ag, rh, G) - np.bincount(hg, ra, G) + 2 * lg * D,
                np.bincount(hi, rh, T) + np.bincount(ai, ra, T) + 2 * lt * (a - prior),
                -np.bincount(ai, rh, T) - np.bincount(hi, ra, T) + 2 * lt * (d - prior),
            ])
            return nll, g

        x0 = np.concatenate([np.full(C, np.log(1.3)), np.full(C, 0.25), np.zeros(2 * G), prior, prior])
        if self.p is not None:  # warm start from the previous fit
            for k, (idx, key) in enumerate([(comps, "base"), (comps, "home"), (groups, "A"),
                                            (groups, "D"), (teams, "a"), (teams, "d")]):
                old = self.p[key]
                seg = x0[sl[k]:sl[k + 1]]
                for j, name in enumerate(idx):
                    if name in old:
                        seg[j] = old[name]
        res = minimize(f, x0, jac=True, method="L-BFGS-B", options={"maxiter": 1000})
        base, home, A, D, a, d = unpack(res.x)

        # rho, holding the Poisson rates fixed
        eh = base[ci] + home[ci] * home_on + A[hg] + a[hi] - D[ag] - d[ai]
        ea = base[ci] + A[ag] + a[ai] - D[hg] - d[hi]
        lh, la = np.exp(eh), np.exp(ea)
        low = (goals_h <= 1) & (goals_a <= 1)
        x_, y_, l_, m_, w_ = goals_h[low], goals_a[low], lh[low], la[low], w[low]

        def rho_nll(r):
            t = np.where((x_ == 0) & (y_ == 0), 1 - l_ * m_ * r,
                np.where((x_ == 0) & (y_ == 1), 1 + l_ * r,
                np.where((x_ == 1) & (y_ == 0), 1 + m_ * r, 1 - r)))
            return -np.sum(w_ * np.log(np.clip(t, 1e-9, None)))

        rho = minimize_scalar(rho_nll, bounds=(-0.2, 0.2), method="bounded").x

        n_eff = np.bincount(hi, w, T) + np.bincount(ai, w, T)
        self.p = {
            "base": dict(zip(comps, base)), "home": dict(zip(comps, home)),
            "A": dict(zip(groups, A)), "D": dict(zip(groups, D)),
            "a": dict(zip(teams, a)), "d": dict(zip(teams, d)),
            "rho": float(rho), "n_eff": dict(zip(teams, n_eff)),
            "fitted_at": now, "promoted": promoted,
        }
        self.last_refit = now

    # --- Model contract -----------------------------------------------------
    def fit(self, history):
        self.p = None
        cols = ["date", "season", "league", "home_id", "away_id", "home_goals", "away_goals", "neutral"]
        self._chunks = [history[cols + [c for c in ("home_xg", "away_xg") if c in history]]]
        self._refit(history.date.max())

    def update(self, played):
        self._chunks.append(played[self._chunks[0].columns])
        now = played.date.max()
        if (now - self.last_refit).days >= self.REFIT_DAYS:
            self._refit(now)

    def rates(self, matches) -> tuple[np.ndarray, np.ndarray]:
        p = self.p
        mean_base = float(np.mean(list(p["base"].values())))
        mean_home = float(np.mean(list(p["home"].values())))
        neutral = matches.neutral.to_numpy() if "neutral" in matches else np.zeros(len(matches), bool)

        def strength(team, key, group_key):
            default = -self.promoted  # never seen: most likely a promoted side
            return p[group_key].get(team_group(team), 0.0) + p[key].get(team, default)

        lam, mu = [], []
        for row, neu in zip(matches.itertuples(index=False), neutral):
            base = p["base"].get(row.league, mean_base)
            home = 0.0 if neu else p["home"].get(row.league, mean_home)
            ah, dh = strength(row.home_id, "a", "A"), strength(row.home_id, "d", "D")
            aa, da = strength(row.away_id, "a", "A"), strength(row.away_id, "d", "D")
            lam.append(np.exp(base + home + ah - da))
            mu.append(np.exp(base + aa - dh))
        return np.array(lam), np.array(mu)

    def predict(self, matches):
        lam, mu = self.rates(matches)
        return np.array([outcome_probs(score_matrix(l, m, self.p["rho"])) for l, m in zip(lam, mu)])

    def goal_rates(self, matches) -> tuple[np.ndarray, np.ndarray]:
        """Expected goals for the goal outputs, with the high-end calibration."""
        lam, mu = self.rates(matches)
        return calibrate_rate(lam), calibrate_rate(mu)

    def matrices(self, matches) -> list[np.ndarray]:
        lam, mu = self.goal_rates(matches)
        return [score_matrix(l, m, self.p["rho"]) for l, m in zip(lam, mu)]

    def experience(self, team) -> float:
        """Weighted number of recent matches behind a team's rating."""
        return float(self.p["n_eff"].get(team, 0.0))

    def ratings(self, reference=None) -> pd.DataFrame:
        """Overall strength on one cross-league scale: expected goal difference
        per match on neutral ground against an average `reference` team (e.g.
        this season's Champions League clubs; default: every team)."""
        p = self.p
        rows = []
        for t in p["a"]:
            g = team_group(t)
            rows.append({"team_id": t, "attack": p["A"].get(g, 0) + p["a"][t],
                         "defence": p["D"].get(g, 0) + p["d"][t], "experience": p["n_eff"][t]})
        df = pd.DataFrame(rows)
        ref = df[df.team_id.isin(reference)] if reference else df
        base = p["base"].get(CL, float(np.mean(list(p["base"].values()))))
        df["xg_for"] = np.exp(base + df.attack - ref.defence.mean())
        df["xg_against"] = np.exp(base + ref.attack.mean() - df.defence)
        df["rating"] = df.xg_for - df.xg_against
        return df.sort_values("rating", ascending=False).reset_index(drop=True)
