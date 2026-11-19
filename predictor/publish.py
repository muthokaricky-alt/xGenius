"""Fit the models on everything known today and write the site's data.

    python -m predictor.publish      # after `python -m predictor.ingest`

Writes web/public/data/:
  predictions.json  upcoming shown fixtures (next DAYS_AHEAD days) + recent results
  history.json      every published pre-kickoff forecast, with the result once known
                    (the live track record; never rewritten after kickoff)
  ratings.json      cross-league power ranking

A forecast is only ever updated before kickoff, so history.json is an honest
record of what the site said. Entries marked "replay" were back-filled from the
walk-forward backtest for matches played before the site went live.
"""
import csv
import datetime as dt
import json
from functools import lru_cache
import sys

import numpy as np
import pandas as pd

from predictor.backtest import OUT_DIR as BACKTEST_DIR
from predictor.backtest import WEB_DATA
from predictor.config import DATA_PROCESSED, ROOT, is_shown, load_coverage
from predictor.data import CL, load_fixtures, load_training
from predictor.leagues import current_season
from predictor.models.dixon_coles import DixonColes, outcome_probs, team_group
from predictor.models.elo import Elo
from predictor.models.ensemble import combine, load_params
from predictor.races import build as build_races
from predictor.teams import load_teams

DAYS_AHEAD = 21
RECENT_DAYS = 21
GRID = 6  # scoreline grid shown on the site: 0..5 goals each

LEAGUE_NAMES = {
    "premier_league": "Premier League", "champions_league": "Champions League",
    "la_liga": "LaLiga", "bundesliga": "Bundesliga", "serie_a": "Serie A", "ligue_1": "Ligue 1",
    "eredivisie": "Eredivisie", "primeira_liga": "Primeira Liga", "belgian_pro": "Belgian Pro League",
    "scottish_prem": "Scottish Premiership", "super_lig": "Süper Lig", "greek_super": "Greek Super League",
    "austrian_bl": "Austrian Bundesliga", "swiss_super": "Swiss Super League",
    "danish_super": "Danish Superliga", "eliteserien": "Eliteserien",
}
STAGES = {
    "LEAGUE_STAGE": "League phase", "GROUP_STAGE": "Group stage", "PLAYOFFS": "Knockout play-offs",
    "LAST_16": "Round of 16", "QUARTER_FINALS": "Quarter-finals", "SEMI_FINALS": "Semi-finals",
    "FINAL": "Final", "REGULAR_SEASON": None,
}
SHORT = {  # tight spaces on phones; everything else uses the full name
    "manchester-united": "Man Utd", "manchester-city": "Man City", "nottingham-forest": "Nott'm Forest",
    "wolverhampton-wanderers": "Wolves", "brighton-and-hove-albion": "Brighton",
    "tottenham-hotspur": "Spurs", "newcastle-united": "Newcastle", "west-ham-united": "West Ham",
    "paris-saint-germain": "PSG", "borussia-dortmund": "Dortmund", "bayern-munich": "Bayern",
    "bayer-leverkusen": "Leverkusen", "atletico-madrid": "Atlético", "sheffield-united": "Sheff Utd",
    "borussia-monchengladbach": "Gladbach", "koln": "Köln", "eintracht-frankfurt": "Frankfurt",
}


def _r(x, n=4):
    return round(float(x), n)


@lru_cache(maxsize=1)
def kit_colours() -> dict:
    """config/kit_colours.csv: each club's shirt colour and its second colour."""
    with open(ROOT / "config" / "kit_colours.csv", encoding="utf-8", newline="") as f:
        return {r["team_id"]: [r["primary"].upper(), r["secondary"].upper()] for r in csv.DictReader(f)}


def team_info(tid: str) -> dict:
    teams, _ = load_teams()
    t = teams.get(tid, {})
    name = t.get("name", tid)
    return {"id": tid, "name": name, "short": SHORT.get(tid, name), "country": t.get("country"),
            "kit": kit_colours().get(tid)}


def adjust(matrix: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Rescale a scoreline matrix so its home/draw/away totals match the ensemble."""
    cur = outcome_probs(matrix)
    m = matrix.copy()
    il = np.tril_indices_from(m, -1)
    iu = np.triu_indices_from(m, 1)
    m[il] *= target[0] / cur[0]
    m[np.diag_indices_from(m)] *= target[1] / cur[1]
    m[iu] *= target[2] / cur[2]
    return m / m.sum()


def describe(matrix: np.ndarray) -> dict:
    g = np.arange(len(matrix))
    xg_h, xg_a = (matrix.sum(axis=1) * g).sum(), (matrix.sum(axis=0) * g).sum()
    total = np.add.outer(g, g)
    flat = [(matrix[i, j], i, j) for i in range(len(g)) for j in range(len(g))]
    top = sorted(flat, reverse=True)[:6]
    return {
        "xg": [_r(xg_h, 2), _r(xg_a, 2)],
        "over25": _r(matrix[total >= 3].sum()),
        "btts": _r(matrix[1:, 1:].sum()),
        "clean_sheet": [_r(matrix[:, 0].sum()), _r(matrix[0, :].sum())],
        "scores": [{"h": int(i), "a": int(j), "p": _r(p)} for p, i, j in top],
        "grid": [[_r(matrix[i, j]) for j in range(GRID)] for i in range(GRID)],
    }


def confidence(dc: DixonColes, home: str, away: str, league: str) -> str:
    exp = min(dc.experience(home), dc.experience(away))
    other = league == CL and "other" in (team_group(home), team_group(away))
    if exp < 6 or (other and exp < 10):
        return "low"
    return "medium" if exp < 15 or other else "high"


def form(train: pd.DataFrame, tid: str, before, n=5) -> list[dict]:
    m = train[((train.home_id == tid) | (train.away_id == tid)) & (train.date < before)].tail(n)
    out = []
    for r in m.itertuples(index=False):
        home = r.home_id == tid
        gf, ga = (r.home_goals, r.away_goals) if home else (r.away_goals, r.home_goals)
        out.append({"date": f"{r.date:%Y-%m-%d}", "opp": team_info(r.away_id if home else r.home_id)["short"],
                    "home": bool(home), "gf": int(gf), "ga": int(ga), "league": r.league,
                    "res": "W" if gf > ga else "D" if gf == ga else "L"})
    return out


PRE = ["odds_pre_h", "odds_pre_d", "odds_pre_a"]


def attach_odds(upcoming: pd.DataFrame, odds: pd.DataFrame) -> pd.DataFrame:
    """Match posted odds to fixtures by teams, allowing a day either way (the
    odds file uses UK dates, fixtures use UTC kickoffs)."""
    up = upcoming.copy()
    for c in PRE:
        up[c] = np.nan
    if odds.empty or up.empty:
        return up
    for i, r in up.iterrows():
        o = odds[(odds.home_id == r.home_id) & (odds.away_id == r.away_id)
                 & ((odds.date - r.date).abs() <= pd.Timedelta(days=1))]
        if len(o):
            up.loc[i, PRE] = o.iloc[0][PRE].to_numpy(float)
    return up


def _load(name, default):
    path = WEB_DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write(name, obj):
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    (WEB_DATA / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def seed_history(history: dict, fx: pd.DataFrame, cov) -> int:
    """Back-fill this season's already-played shown matches from the walk-forward
    backtest (out-of-sample by construction), marked as replay."""
    path = BACKTEST_DIR / "ensemble.csv"
    if not path.exists():
        return 0
    bt = pd.read_csv(path, parse_dates=["date"])
    bt = bt[bt.season == current_season()]
    done = fx[fx.status.eq("FINISHED") & fx.home_id.notna() & fx.away_id.notna()].copy()
    done["date"] = done.kickoff.dt.tz_localize(None).dt.normalize()
    j = done.merge(bt[["date", "home_id", "away_id", "p_home", "p_draw", "p_away"]],
                   on=["date", "home_id", "away_id"])
    added = 0
    for r in j.itertuples(index=False):
        key = str(r.match_id)
        if key in history or not is_shown(r.league, r.home_id, r.away_id, cov):
            continue
        history[key] = {"id": int(r.match_id), "kickoff": r.kickoff.isoformat(), "league": r.league,
                        "home": r.home_id, "away": r.away_id,
                        "p": [_r(r.p_home), _r(r.p_draw), _r(r.p_away)], "source": "replay"}
        added += 1
    return added


def main():
    now = pd.Timestamp.now(tz="UTC")
    train = load_training()
    fx = load_fixtures()
    if fx.empty:
        raise SystemExit("no fixtures.csv: run `python -m predictor.ingest` with an API key first")
    cov = load_coverage()
    params = load_params()

    print(f"fitting on {len(train):,} matches up to {train.date.max():%Y-%m-%d}...", flush=True)
    elo, dc = Elo(), DixonColes()
    elo.fit(train)
    dc.fit(train)

    mapped = fx.home_id.notna() & fx.away_id.notna()
    upcoming = fx[mapped & fx.status.isin(["SCHEDULED", "TIMED"]) & (fx.kickoff > now)
                  & (fx.kickoff <= now + pd.Timedelta(days=DAYS_AHEAD)) & fx.shown.astype(bool)]
    upcoming = upcoming.sort_values("kickoff").copy()
    upcoming["date"] = upcoming.kickoff.dt.tz_localize(None).dt.normalize()
    upcoming["season"] = [current_season(d.date()) for d in upcoming.date]
    upcoming["neutral"] = upcoming.stage.eq("FINAL")

    # Pre-match market odds for upcoming domestic matches, when already posted
    odds_path = DATA_PROCESSED / "odds_upcoming.csv"
    odds = pd.read_csv(odds_path, parse_dates=["date"]) if odds_path.exists() else pd.DataFrame()
    upcoming = attach_odds(upcoming, odds)

    rows = []
    if len(upcoming):
        blind = upcoming[["date", "season", "league", "home_id", "away_id", "neutral"]]
        p_elo, p_dc = elo.predict(blind), dc.predict(blind)
        p_ens, used = combine(p_elo, p_dc, upcoming[PRE].to_numpy(float),
                              upcoming.league.eq(CL).to_numpy(), params)
        for r, pe, mat, um in zip(upcoming.itertuples(index=False), p_ens, dc.matrices(blind), used):
            rows.append({
                "id": int(r.match_id), "kickoff": r.kickoff.isoformat(), "league": r.league,
                "stage": STAGES.get(r.stage, None) if r.league == CL else None,
                "home": team_info(r.home_id), "away": team_info(r.away_id),
                "p": [_r(x) for x in pe], **describe(adjust(mat, pe)),
                "confidence": confidence(dc, r.home_id, r.away_id, r.league),
                "market": bool(um),
                "form": {"home": form(train, r.home_id, r.date), "away": form(train, r.away_id, r.date)},
            })

    # History: upsert forecasts for matches not yet kicked off; attach results.
    history = {str(h["id"]): h for h in _load("history.json", {"matches": []})["matches"]}
    seeded = seed_history(history, fx, cov)
    for m in rows:
        prev = history.get(str(m["id"]))
        if prev is None or prev.get("source") != "replay":
            history[str(m["id"])] = {"id": m["id"], "kickoff": m["kickoff"], "league": m["league"],
                                     "home": m["home"]["id"], "away": m["away"]["id"], "p": m["p"],
                                     "xg": m["xg"], "top": m["scores"][0], "source": "live",
                                     "market": m["market"],
                                     "published_at": now.isoformat(timespec="seconds")}
    finished = fx[fx.status.eq("FINISHED") & fx.home_goals.notna()]
    finished = finished.set_index(finished.match_id.astype(str))
    for key, h in history.items():
        if key in finished.index and "result" not in h:
            f = finished.loc[key]
            h["result"] = [int(f.home_goals), int(f.away_goals)]
    hist = sorted(history.values(), key=lambda h: h["kickoff"])

    recent_cut = (now - pd.Timedelta(days=RECENT_DAYS)).isoformat()
    recent = [{**h, "home": team_info(h["home"]), "away": team_info(h["away"])}
              for h in hist if "result" in h and h["kickoff"] >= recent_cut]

    leagues_shown = sorted({r["league"] for r in rows} | {h["league"] for h in recent},
                           key=lambda lg: list(LEAGUE_NAMES).index(lg))
    _write("predictions.json", {
        "generated_at": now.isoformat(timespec="seconds"),
        "data_through": f"{train.date.max():%Y-%m-%d}",
        "leagues": {lg: LEAGUE_NAMES[lg] for lg in leagues_shown},
        "matches": rows, "recent": list(reversed(recent)),
    })
    _write("history.json", {"generated_at": now.isoformat(timespec="seconds"), "matches": hist})

    # Ratings: teams that played in the last ~8 months, enough matches to mean something
    last = pd.concat([train[["date", "home_id", "league"]].rename(columns={"home_id": "team"}),
                      train[["date", "away_id", "league"]].rename(columns={"away_id": "team"})])
    dom = last[last.league != CL].sort_values("date").groupby("team").tail(1).set_index("team")
    seen = last.groupby("team").date.max()
    cl_recent = train[(train.league == CL) & (train.date >= train.date.max() - pd.Timedelta(days=365))]
    r = dc.ratings(reference=set(cl_recent.home_id) | set(cl_recent.away_id))
    r = r[r.team_id.map(seen).ge(train.date.max() - pd.Timedelta(days=240)) & (r.experience >= 5)]
    ratings = []
    for i, x in enumerate(r.itertuples(index=False), 1):
        lg = dom.league.get(x.team_id)
        ratings.append({"rank": i, **team_info(x.team_id), "league": lg,
                        "league_name": LEAGUE_NAMES.get(lg, "Champions League only"),
                        "rating": _r(x.rating, 3), "xg_for": _r(x.xg_for, 2), "xg_against": _r(x.xg_against, 2),
                        "elo": _r(elo.rating[x.team_id], 0) if x.team_id in elo.rating else None,
                        "experience": _r(x.experience, 1)})
    _write("ratings.json", {"generated_at": now.isoformat(timespec="seconds"),
                            "note": "Expected goal difference per match against an average Champions League side on neutral ground.",
                            "teams": ratings})

    # Season races: scorers, assists, clean sheets per shown competition
    scorers_path = DATA_PROCESSED / "scorers.csv"
    scorers = pd.read_csv(scorers_path) if scorers_path.exists() else pd.DataFrame()
    race_leagues = [lg for lg in LEAGUE_NAMES if lg in ("premier_league", "champions_league", "la_liga",
                                                         "bundesliga", "serie_a", "ligue_1")]
    races = build_races(train, fx, scorers, dc, now, race_leagues, team_info)
    for r in races:
        r["name"] = LEAGUE_NAMES[r["league"]]
    _write("races.json", {"generated_at": now.isoformat(timespec="seconds"),
                          "data_through": f"{train.date.max():%Y-%m-%d}", "competitions": races})

    live = sum(h.get("source") == "live" for h in hist)
    print(f"predictions.json: {len(rows)} upcoming ({sum(r['market'] for r in rows)} with market odds), "
          f"{len(recent)} recent results")
    print(f"history.json: {len(hist)} forecasts ({live} live, {len(hist) - live} replay; {seeded} back-filled now)")
    print(f"ratings.json: {len(ratings)} teams")
    print(f"races.json: {len(races)} competitions"
          + ("" if not scorers.empty else " (no scorers.csv: player races empty)"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
