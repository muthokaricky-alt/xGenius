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
| `config/coverage.json` | Which leagues/teams are shown. JSON so Python and JS both read it natively. |
| `predictor/` | Python package: ingestion, models, backtesting |
| `tests/` | Python tests (pytest) |
| `data/raw/` | Downloaded data cache (gitignored, re-fetchable) |
| `web/` | React + Vite frontend |

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
2. [ ] Data ingestion + team-name mapping
3. [ ] Backtest harness + Elo baseline
4. [ ] Dixon-Coles Poisson
5. [ ] xG features
6. [ ] Gradient boosting + ensemble + calibration
7. [ ] Champions League cross-league strength
8. [ ] Automated pipeline (GitHub Actions → static JSON)
9. [ ] Frontend
10. [ ] Deployment (Cloudflare Pages)

**Parked:** user predictions + leaderboard, to come back later as "beat the model".
