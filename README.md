# ⚽ Match Predictor

Predicts football match outcomes with statistical models: home/draw/away probabilities, likely scorelines, expected goals, over/under 2.5 and both-teams-to-score. It's a stats project, not a betting tool.

**Coverage** (edit `config/coverage.json`):
- Every match: Premier League, Champions League
- Big clubs only: Bayern, Dortmund · Juventus, Inter, Milan, Napoli, Roma, Lazio · PSG · Barcelona, Real Madrid, Atlético

Models train on **all** matches in those leagues. The coverage file only controls what's shown.

## Architecture

```
GitHub Actions (scheduled, free)          Cloudflare Pages (free, static)
  fetch data → fit models → predict  ──▶   web/ reads predictions/*.json
  → commit static JSON
```

No always-on server, no database, no cold starts. Training runs offline in Python; the site is plain static files.

## Repo layout

| Path | What |
|---|---|
| `config/coverage.json` | Which leagues/teams are shown. JSON so Python and JS both read it natively. Team names can be any alias. |
| `config/teams.csv` | Team-name mapping: `team_id, name, country, aliases`. Edit by hand. |
| `predictor/leagues.py` | Leagues ingested and their code in each source |
| `predictor/ingest/` | Downloaders (cached) + `python -m predictor.ingest` |
| `predictor/teams.py` | Name normalisation and alias lookup |
| `predictor/models/` | Models (`fit` / `predict` / `update` contract): base rate, Elo |
| `predictor/metrics.py` | Log loss, Brier, RPS, accuracy; odds → probabilities |
| `predictor/backtest.py` | Walk-forward backtest + tuning: `python -m predictor.backtest [--tune]` |
| `tests/` | Python tests (pytest) |
| `data/raw/` | Download cache (gitignored, re-fetchable) |
| `data/processed/` | Clean tables built by ingestion, plus `backtest/` predictions (gitignored, rebuildable) |
| `web/` | React + Vite frontend |

## Data

| Source | Gives us | Notes |
|---|---|---|
| [football-data.co.uk](https://football-data.co.uk) | Results + bookmaker odds, 2014/15 onwards, 15 leagues | Free CSVs. xG only from 2026/27 (see below). |
| [football-data.org](https://www.football-data.org) | Fixtures, Champions League | Free API key, 10 requests/min. Champions League results only from 2023/24 on the free tier. |

We ingest 10 leagues beyond the 5 we show (Netherlands, Portugal, Belgium, Scotland, Turkey, Greece, Austria, Switzerland, Denmark, Norway). Their clubs play in the Champions League, so we need ratings for them.

**xG:** the 2026/27 files have `HxG`/`AxG` (→ `home_xg`/`away_xg`) for the 11 one-file-per-season leagues; the four all-seasons files (Austria, Switzerland, Denmark, Norway) have none, and no earlier season has any. football-data.co.uk doesn't say who computes it: its notes only define the column, and its credits list match statistics from BBC, Flashscore, ESPN and league sites, without naming an xG provider. Treat it as an unverified xG model of unknown origin; milestone 5 should check it against results before trusting it.

**API rate limit:** the client follows football-data.org's `X-Requests-Available-Minute` / `X-RequestCounter-Reset` headers, falls back to 6.5 s between calls if they're missing, and on a 429 waits for the reset and retries once.

Odds columns: `odds_pre_*` (known before kickoff, allowed as a feature), `odds_close_*` and `pin_close_*` (closing odds, **evaluation benchmark only**, never a feature: that would be leakage).

Knockout matches use the **90-minute** score; extra time and penalties would distort a goals model.

**Team names:** every spelling is normalised (accents, punctuation, "FC"/"CF"/etc. stripped), then looked up in `config/teams.csv`. A test fails if one alias points at two teams (e.g. "Paris" would match PSG and Paris FC).

```powershell
python -m predictor.ingest
```
```powershell
python -m predictor.teams check
```

## Setup (Windows / PowerShell)

Requires Python 3.11+ and Node 18+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

If `Activate.ps1` is blocked, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Run the tests:

```powershell
pytest
```

Run the frontend:

```powershell
cd web
npm install
npm run dev
```

## Model leaderboard

Walk-forward backtest; lower log loss is better. A change only goes in if it beats the current best.

| Model | Log loss | Brier | RPS | Accuracy | Notes |
|---|---|---|---|---|---|
| _none yet_ | | | | | Milestone 3 |

## Roadmap

1. [x] Repo restructure
2. [x] Data ingestion + team-name mapping
3. [ ] Backtest harness + Elo baseline
4. [ ] Dixon-Coles Poisson
5. [ ] xG features
6. [ ] Gradient boosting + ensemble + calibration
7. [ ] Champions League cross-league strength
8. [ ] Automated pipeline (GitHub Actions → static JSON)
9. [ ] Frontend
10. [ ] Deployment (Cloudflare Pages)

**Parked:** user predictions + leaderboard, to come back later as "beat the model".
