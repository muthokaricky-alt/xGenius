"""Season-end projections: top scorers, top assisters and clean sheets per
competition.

Clean sheets (teams)
  current total + one Bernoulli per remaining fixture, with the chance that
  the opponent scores 0 taken from the Dixon-Coles score matrix.

Goals and assists (players)
  A player's share of his team's goals in this competition so far, shrunk
  toward zero for small samples:  share = goals / (team_goals + SHRINK).
  Projected extra goals ~ Poisson(share * expected team goals in the
  remaining fixtures). Assists use the same share logic on assists.

Each race is simulated N_SIMS times to get a likely range (10th-90th
percentile of the final total) and each contender's chance of finishing top
(shared first place counts as a share of the win).

Limits, stated on the site: no minutes, injuries, suspensions or penalty duty;
team strength is held fixed for the rest of the season; Champions League
projections only cover fixtures already drawn (no knockout rounds until they
are scheduled); the free data lists only players with at least one goal, so
assist-only players are missing from the assist race.
"""
import numpy as np
import pandas as pd

from predictor.data import CL
from predictor.leagues import current_season
from predictor.models.dixon_coles import score_matrix

SHRINK = 3.0      # pseudo team-goals added to the denominator of a player's share
N_SIMS = 20000
TOP = 15


def remaining_fixtures(fx: pd.DataFrame, now) -> pd.DataFrame:
    """This season's scheduled fixtures (both teams mapped) not yet kicked off."""
    f = fx[fx.status.isin(["SCHEDULED", "TIMED"]) & fx.home_id.notna() & fx.away_id.notna()
           & (fx.kickoff > now)].copy()
    f["date"] = f.kickoff.dt.tz_localize(None).dt.normalize()
    f["season"] = [current_season(d.date()) for d in f.date]
    f["neutral"] = f.stage.eq("FINAL")
    return f[f.season == current_season(now.date())]


def team_outlook(dc, remaining: pd.DataFrame) -> pd.DataFrame:
    """One row per (team, remaining fixture): expected goals for, clean-sheet chance."""
    if remaining.empty:
        return pd.DataFrame(columns=["league", "team_id", "xg", "p_cs"])
    blind = remaining[["date", "season", "league", "home_id", "away_id", "neutral"]]
    lam, mu = dc.rates(blind)
    rows = []
    for r, l, m in zip(blind.itertuples(index=False), lam, mu):
        mat = score_matrix(l, m, dc.p["rho"])
        rows.append({"league": r.league, "team_id": r.home_id, "xg": l, "p_cs": mat[:, 0].sum()})
        rows.append({"league": r.league, "team_id": r.away_id, "xg": m, "p_cs": mat[0, :].sum()})
    return pd.DataFrame(rows)


def team_so_far(train: pd.DataFrame, season: int) -> pd.DataFrame:
    """Per (league, team) this season: matches, goals for, clean sheets."""
    t = train[train.season == season]
    home = pd.DataFrame({"league": t.league, "team_id": t.home_id, "gf": t.home_goals, "cs": t.away_goals.eq(0)})
    away = pd.DataFrame({"league": t.league, "team_id": t.away_id, "gf": t.away_goals, "cs": t.home_goals.eq(0)})
    both = pd.concat([home, away])
    return both.groupby(["league", "team_id"]).agg(played=("gf", "size"), gf=("gf", "sum"),
                                                     cs=("cs", "sum")).reset_index()


def simulate(current: np.ndarray, draws: np.ndarray) -> dict:
    """`draws` is (N_SIMS, n) of future totals. Returns final means, ranges and P(top)."""
    final = current[None, :] + draws
    best = final.max(axis=1, keepdims=True)
    at_top = final == best
    p_top = (at_top / at_top.sum(axis=1, keepdims=True)).mean(axis=0)
    return {"mean": final.mean(axis=0), "lo": np.percentile(final, 10, axis=0),
            "hi": np.percentile(final, 90, axis=0), "p_top": p_top}


def player_race(scorers: pd.DataFrame, so_far: pd.DataFrame, outlook: pd.DataFrame,
                stat: str, rng) -> pd.DataFrame:
    s = scorers[scorers.team_id.notna() & (scorers[stat] > 0)].copy()
    if s.empty:
        return s
    future_xg = outlook.groupby("team_id").xg.sum()
    team_gf = so_far.set_index("team_id").gf
    s["team_goals"] = s.team_id.map(team_gf).fillna(0)
    s["share"] = s[stat] / (s.team_goals.clip(lower=s[stat]) + SHRINK)
    s["future"] = s.share * s.team_id.map(future_xg).fillna(0)
    sim = simulate(s[stat].to_numpy(float), rng.poisson(s.future.to_numpy(), (N_SIMS, len(s))))
    return s.assign(projected=sim["mean"], lo=sim["lo"], hi=sim["hi"], p_top=sim["p_top"])


def clean_sheet_race(so_far: pd.DataFrame, outlook: pd.DataFrame, rng) -> pd.DataFrame:
    teams = sorted(set(so_far.team_id) | set(outlook.team_id))
    cur = so_far.set_index("team_id").reindex(teams)
    probs = [outlook.p_cs[outlook.team_id == t].to_numpy() for t in teams]
    n_max = max((len(p) for p in probs), default=0)
    pm = np.zeros((len(teams), n_max))
    for i, p in enumerate(probs):
        pm[i, :len(p)] = p
    draws = (rng.random((N_SIMS, len(teams), n_max)) < pm[None]).sum(axis=2) if n_max else np.zeros((N_SIMS, len(teams)))
    sim = simulate(cur.cs.fillna(0).to_numpy(float), draws)
    return pd.DataFrame({"team_id": teams, "played": cur.played.fillna(0).astype(int).to_numpy(),
                         "cs": cur.cs.fillna(0).astype(int).to_numpy(),
                         "remaining": [len(p) for p in probs], "projected": sim["mean"],
                         "lo": sim["lo"], "hi": sim["hi"], "p_top": sim["p_top"]})


def build(train, fx, scorers, dc, now, leagues, team_info, seed=0) -> list[dict]:
    rng = np.random.default_rng(seed)
    season = current_season(now.date())
    remaining = remaining_fixtures(fx, now)
    outlook_all = team_outlook(dc, remaining[remaining.league.isin(leagues)])
    so_far_all = team_so_far(train, season)
    out = []
    for lg in leagues:
        outlook = outlook_all[outlook_all.league == lg]
        so_far = so_far_all[so_far_all.league == lg]
        sc = scorers[scorers.league == lg] if not scorers.empty else scorers
        if so_far.empty and outlook.empty:
            continue

        def players(stat):
            r = player_race(sc, so_far, outlook, stat, rng)
            if r.empty:
                return []
            r = r.sort_values(["projected", stat], ascending=False).head(TOP)
            return [{"player": x.player, "team": team_info(x.team_id), stat: int(getattr(x, stat)),
                     "played": int(x.played), "projected": round(float(x.projected), 1),
                     "range": [int(x.lo), int(x.hi)], "p_top": round(float(x.p_top), 3)}
                    for x in r.itertuples(index=False)]

        cs = clean_sheet_race(so_far, outlook, rng).sort_values(["projected", "cs"], ascending=False).head(TOP)
        out.append({
            "league": lg,
            "remaining_fixtures": int(len(remaining[remaining.league == lg])),
            "scorers": players("goals"),
            "assists": players("assists"),
            "clean_sheets": [{"team": team_info(x.team_id), "cs": int(x.cs), "played": int(x.played),
                              "remaining": int(x.remaining), "projected": round(float(x.projected), 1),
                              "range": [int(x.lo), int(x.hi)], "p_top": round(float(x.p_top), 3)}
                             for x in cs.itertuples(index=False)],
        })
    return out
