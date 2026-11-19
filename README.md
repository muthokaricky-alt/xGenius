# ⚽ xGenius

Predicts football match outcomes with statistical models: home/draw/away probabilities, likely scorelines, expected goals, over/under 2.5 and both-teams-to-score. It's a stats project, not a betting tool.

**Coverage** (edit `config/coverage.json`):
- Every match: Premier League, Champions League
- Big clubs only: Bayern, Dortmund · Juventus, Inter, Milan, Napoli, Roma, Lazio · PSG · Barcelona, Real Madrid, Atlético

Models train on **all** matches in 15 leagues plus the Champions League. The coverage file only controls what's shown.

## Architecture

```
GitHub Actions (every 6 h, free)                     Cloudflare Pages (free, static)
  ingest → fit Elo + Dixon-Coles → publish   ──▶     web/ reads web/public/data/*.json
  → commit web/public/data/*.json                    (redeploys on every push)
```

No always-on server, no database, no cold starts. Training runs in Python on a schedule; the site is plain static files.

## Repo layout

| Path | What |
|---|---|
| `config/coverage.json` | Which leagues/teams are shown. Team names can be any alias. |
| `config/teams.csv` | Team-name mapping: `team_id, name, country, aliases`. Edit by hand. |
| `config/kit_colours.csv` | Each shown club's shirt colour and second colour (used by the site only). |
| `config/ensemble.json` | Ensemble weights, fitted by `python -m predictor.backtest --fit-ensemble`. |
| `predictor/leagues.py` | Leagues ingested and their code in each source |
| `predictor/ingest/` | Downloaders (cached) + `python -m predictor.ingest` |
| `predictor/teams.py` | Name normalisation and alias lookup |
| `predictor/data.py` | One training table: domestic + Champions League results |
| `predictor/models/` | Models (`fit` / `predict` / `update` contract): base rate, Elo, Dixon-Coles, ensemble |
| `predictor/metrics.py` | Log loss, Brier, RPS, accuracy; odds → probabilities |
| `predictor/backtest.py` | Walk-forward backtest, tuning, ensemble fitting; writes `performance.json` |
| `predictor/races.py` | Season-end projections: top scorers, assists, clean sheets |
| `predictor/publish.py` | Fits on everything known today and writes the site's JSON |
| `web/` | React + Vite site; `web/public/data/` is the published data |
| `.github/workflows/` | `update.yml` (every 6 h), `backtest.yml` (weekly), `ci.yml` (tests + build) |
| `PRODUCT.md`, `DESIGN.md` | Who the site is for, and its design system |
| `tests/` | Python tests (pytest) |
| `data/raw/`, `data/processed/` | Download cache and built tables (gitignored, rebuildable) |

## Data

| Source | Gives us | Notes |
|---|---|---|
| [football-data.co.uk](https://football-data.co.uk) | Results + bookmaker odds, 2014/15 onwards, 15 leagues | Free CSVs. xG only from 2026/27 (see below). |
| [football-data.org](https://www.football-data.org) | Fixtures, Champions League, top scorers | Free API key, 10 requests/min. Champions League results only from 2023/24 on the free tier. Scorers: top 100 per competition, this season only; players without a goal are not listed (so assist-only players are missing). |

We ingest 10 leagues beyond the 5 we show (Netherlands, Portugal, Belgium, Scotland, Turkey, Greece, Austria, Switzerland, Denmark, Norway). Their clubs play in the Champions League, so we need ratings for them.

**xG:** the 2026/27 files have `HxG`/`AxG` (→ `home_xg`/`away_xg`) for the 11 one-file-per-season leagues; the four all-seasons files (Austria, Switzerland, Denmark, Norway) have none, and no earlier season has any. football-data.co.uk doesn't say who computes it. Milestone 5 checked it against results: total goals are 1.016× total xG, per-match correlation with goals is 0.61, and the side with more xG won 77% of decisive matches, all in line with established xG models. Blending it into Dixon-Coles at 50% improved log loss on Sep–Nov 2026 matches by 0.0023 ± 0.0025 (588 matches): positive but not yet significant. It's switched on (`xg_weight=0.5`); **re-check at the end of 2026/27** with a full season.

**API rate limit:** the client follows football-data.org's `X-Requests-Available-Minute` / `X-RequestCounter-Reset` headers, falls back to 6.5 s between calls if they're missing, and on a 429 waits for the reset and retries once.

Odds columns: `odds_pre_*` (known before kickoff), `odds_close_*` and `pin_close_*` (closing odds, **evaluation benchmark only**, never a feature: that would be leakage). The models use no odds at all.

Knockout matches use the **90-minute** score; extra time and penalties would distort a goals model.

**Team names:** every spelling is normalised (accents, punctuation, "FC"/"CF"/etc. stripped), then looked up in `config/teams.csv`. A test fails if one alias points at two teams (e.g. "Paris" would match PSG and Paris FC).

## Setup (Windows / PowerShell)

Requires Python 3.11+ and Node 22+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then put your football-data.org key in .env
```

If `Activate.ps1` is blocked, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Run the whole pipeline locally:

```powershell
python -m predictor.ingest      # download results + fixtures
python -m predictor.backtest    # optional, ~1.5 min: leaderboard + performance.json
python -m predictor.publish     # predictions.json, history.json, ratings.json
pytest
```

Run the site:

```powershell
cd web
npm install
npm run dev
```

## Models

- **Elo** (`models/elo.py`): per-league ratings with a goal-difference multiplier, season regression and a promoted-team penalty; an ordered logit turns rating gaps into home/draw/away.
- **Dixon-Coles** (`models/dixon_coles.py`): Poisson goals with the low-score correction, fitted jointly on every league and the Champions League, time-decayed (half-life 300 days), ridge-regularised. Gives the scoreline grid, xG, over/under and BTTS.
- **Ensemble** (`models/ensemble.py`): a logarithmic pool of the two with per-outcome calibration biases, fitted on the validation seasons. Champions League forecasts use Dixon-Coles alone. The site's scoreline grid is rescaled to match the ensemble's home/draw/away.

**Cross-league strength (milestone 7).** Each team's attack and defence is a country offset plus a team effect. Domestic matches can't see the country offsets; Champions League matches pin them down, which puts every club on one scale. Clubs from countries we don't ingest (Slavia, Qarabağ, Kairat...) share one "other" group, so they borrow strength from each other's European results, and their forecasts are flagged low-confidence until they have played enough. This replaced the earlier plan of a prior from UEFA country coefficients: it needs no hand-maintained coefficient file, and the shrinkage strength was tuned on the 2024/25 Champions League (1.0016 → 0.9186 log loss vs the base rate). A coefficient-based prior for the "other" group remains a possible refinement.

## Season races

`races.json` projects end-of-season totals for every shown competition, simulated 20,000 times (likely range = 10th–90th percentile, plus each contender's chance of finishing top):

- **Clean sheets (teams):** current total + the Dixon-Coles chance that the opponent scores 0 in each remaining fixture. Backtested from 19 Nov 2025 to the end of 2025/26 (96 teams, 5 leagues): mean absolute error 2.11 clean sheets per team vs 3.32 for extending each team's pace; team goals 5.75 vs 7.39.
- **Goals and assists (players):** a player keeps their share of the team's goals in that competition so far (`goals / (team goals + 3)`), applied to the team's expected goals in its remaining fixtures. Not backtested (no historical mid-season scorer data on the free tier). Blind to minutes, injuries, transfers and penalty duty.
- Champions League projections cover scheduled fixtures only; knockout rounds count once drawn.

## Model leaderboard

Walk-forward backtest; lower log loss is better. A change only goes in if it beats the current best.

Test period 2018/19 to 2025/26 (8 seasons, 15 leagues, 32,123 matches with Pinnacle closing odds). Hyperparameters and ensemble weights are fitted on 2016/17 to 2017/18 only. Reproduce with `python -m predictor.backtest`.

| Model | Log loss | Brier | RPS | Accuracy | Notes |
|---|---|---|---|---|---|
| **Ensemble** | **0.9834** | **0.5858** | **0.2001** | 52.2% | Elo + Dixon-Coles, calibrated; what the site publishes |
| Elo | 0.9845 | 0.5865 | 0.2004 | 52.3% | k=12, regress 0.1, promoted −50; ordered-logit draw model |
| Dixon-Coles | 0.9858 | 0.5873 | 0.2007 | 52.0% | joint cross-league fit, half-life 300 d |
| Base rate | 1.0735 | 0.6497 | 0.2306 | 43.5% | league H/D/A frequencies; the floor |
| _Market (Pinnacle closing)_ | _0.9646_ | _0.5730_ | _0.1941_ | _53.6%_ | _benchmark only, not known at publish time_ |

The ensemble closes 83% of the gap between the base rate and the closing market.

**Champions League** 2024/25–2025/26 (378 matches): ensemble 0.9215 log loss (56.6% accuracy), Dixon-Coles 0.9221, base rate 1.0121.

## Deployment

The site deploys to **Cloudflare Pages** (static, free, global CDN, no cold starts, and every data commit redeploys it automatically).

1. **API key for the scheduled updates.** On GitHub: repo → *Settings* → *Secrets and variables* → *Actions* → *New repository secret*. Name `FOOTBALL_DATA_API_KEY`, value = your football-data.org key (the one in your local `.env`).
2. **Merge to `main`.** Scheduled workflows only run on the default branch.
3. **Cloudflare Pages.** dash.cloudflare.com → *Workers & Pages* → *Create* → *Pages* → *Connect to Git* → pick `xGenius`, then:
   - Production branch: `main`
   - Framework preset: *Vite* (or None)
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Root directory: `web`
   - Environment variable: `NODE_VERSION` = `24`
4. **First data run.** GitHub → *Actions* → *Update predictions* → *Run workflow*. After that it runs every 6 hours, and *Weekly backtest* every Monday.

## Roadmap

1. [x] Repo restructure
2. [x] Data ingestion + team-name mapping
3. [x] Backtest harness + Elo baseline
4. [x] Dixon-Coles Poisson
5. [x] xG features (on at 50%; re-check after a full season)
6. [x] Ensemble + calibration (gradient boosting dropped: with two model outputs as the only inputs it has nothing to add, and the data has no lineups or injuries)
7. [x] Champions League cross-league strength
8. [x] Automated pipeline (GitHub Actions → static JSON)
9. [x] Frontend
10. [ ] Deployment (Cloudflare Pages): steps above

**Parked:** user predictions + leaderboard, to come back later as "beat the model".
