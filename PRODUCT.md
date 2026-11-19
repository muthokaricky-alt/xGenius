# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Public football fans who find the site: they follow the Premier League, the Champions League and Europe's big clubs, and want to know how this weekend's matches are likely to go. Not assumed to know what xG, log loss or a probability distribution is; comfortable with percentages.

## Product Purpose
xGenius forecasts football matches with statistical models: home/draw/away probabilities, likely scorelines, expected goals, over/under 2.5 goals and both-teams-to-score. Success: a fan can see the next fixtures at a glance, open any match and understand why the model leans the way it does, and trust the numbers because the model's track record is shown openly.

## Positioning
Model-driven and honest: every number comes from models backtested out of sample over eight seasons and 32,000 matches, the track record (including misses) is public, and the site says plainly that bookmakers' closing odds are still more accurate. It is a stats project, not a betting tool: no tips, no odds, no affiliate links.

## Operating Context
- Fans check before a matchday, often on a phone.
- Data refreshes automatically every 6 hours (GitHub Actions); the site is static (Cloudflare Pages) and reads JSON from `web/public/data/`.
- Coverage: every Premier League and Champions League match; Bayern, Dortmund, Juventus, Inter, Milan, Napoli, Roma, Lazio, PSG, Barcelona, Real Madrid and Atlético in their domestic leagues.

## Capabilities and Constraints
- Per match: P(home/draw/away), expected goals, 6×6 scoreline grid, top scorelines, over 2.5, BTTS, clean-sheet chances, last-5 form, confidence (high/medium/low by how much recent data backs both teams).
- Recent results with the pre-match forecast; live track record from `history.json` (entries marked "replay" were back-filled from the walk-forward backtest and must be labelled as such).
- Cross-league power ranking (`ratings.json`): expected goal difference vs an average Champions League side.
- Backtest leaderboard and calibration (`performance.json`).
- No user accounts, predictions game or leaderboard of users (parked for later).
- No club crests: no licensed source; teams are identified by name.

## Brand Commitments
- Name: xGenius, with "xG" highlighted in the wordmark.
- Light and dark themes.

## Evidence on Hand
Real model outputs and backtest metrics in `web/public/data/`. No testimonials, users or press exist; never invent them.

## Product Principles
1. Fixtures first: the next matches and their probabilities are the product.
2. Explain, don't assume: every stat has a plain-language reading for a casual fan.
3. Show the misses: accuracy is reported honestly, including where the market beats us.
4. Probabilities, not certainties: language and visuals never imply a sure thing.

## Accessibility & Inclusion
WCAG 2.2 AA: colour is never the only carrier of meaning (probabilities always have numbers), keyboard navigable, respects reduced motion.
