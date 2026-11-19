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

Test period 2018/19 to 2025/26 (8 seasons, 15 leagues, 32,123 matches with Pinnacle closing odds). Hyperparameters are tuned on 2016/17 to 2017/18 only. Reproduce with `python -m predictor.backtest`.

| Model | Log loss | Brier | RPS | Accuracy | Notes |
|---|---|---|---|---|---|
| Elo | 0.9845 | 0.5865 | 0.2004 | 52.3% | k=12, regress 0.1, promoted −50; ordered-logit draw model |
| Base rate | 1.0735 | 0.6497 | 0.2306 | 43.5% | league H/D/A frequencies; the floor |
| _Market (Pinnacle closing)_ | _0.9646_ | _0.5730_ | _0.1941_ | _53.6%_ | _benchmark only, not known at publish time_ |

## Roadmap

1. [x] Repo restructure
2. [x] Data ingestion + team-name mapping
3. [x] Backtest harness + Elo baseline
4. [ ] Dixon-Coles Poisson
5. [ ] xG features
6. [ ] Gradient boosting + ensemble + calibration
7. [ ] Champions League cross-league strength
8. [ ] Automated pipeline (GitHub Actions → static JSON)
9. [ ] Frontend
10. [ ] Deployment (Cloudflare Pages)

**Parked:** user predictions + leaderboard, to come back later as "beat the model".

### Milestone 7 plan: Champions League teams from leagues we don't ingest

Clubs such as Slavia/Sparta Praha (Czechia), Pafos (Cyprus), Qarabağ/Sabah (Azerbaijan), Kairat (Kazakhstan), Crvena Zvezda (Serbia), Dinamo Zagreb, Slovan Bratislava and Shakhtar have no domestic data here. They get a **fallback rating from the UEFA country coefficient**:

1. Once milestone 7 has put the 15 ingested leagues on one cross-league scale, take each country's **average rating of its CL participants** (not the league average: CL clubs are the top of their league).
2. Fit `rating ≈ a + b · log(5-year UEFA country coefficient)` across those 15 countries. Use the log because coefficients are skewed: the top countries score several times the mid-ranked ones, and the playing gap doesn't grow that fast.
3. An uncovered club starts at the fitted value for its country, with a wider uncertainty.
4. Every CL match it plays updates the rating like any other team's, so the prior matters less as the season goes on. Predictions involving a team still mostly on its prior are flagged "low confidence".

Why the country coefficient: we don't have these leagues' matches, so "league strength" has to come from outside, and the country coefficient is UEFA's own published, cross-league measure of exactly that (5 seasons of European results). It's also stable and one number per country. Club coefficients were considered but rejected as the default: they lag (5-year window), and under UEFA's rules small clubs' values have been floored at a share of the country coefficient, so they largely repeat it (check the current rule before relying on this). They can be tried as a refinement if they beat the country version in the backtest.

Data: `config/uefa_country_coefficients.csv`, edited by hand once a year (UEFA has no free API; scraping is fragile). Validation: pretend Austria, Switzerland, Denmark and Norway aren't ingested, rate their clubs from coefficients alone, and compare those CL predictions with the full-data ones. Limits: free-tier CL history only starts in 2023/24, and qualifying rounds aren't covered, so these clubs have few matches to learn from.
