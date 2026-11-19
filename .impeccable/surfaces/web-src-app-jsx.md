---
version: 1
slug: "web-src-app-jsx"
primary_target: "web/src/App.jsx"
related_targets: []
---

# xGenius web app

Scope: the whole web app (Matches, Match detail, Ratings, Track record, How it works). Mode: Operate.
Audience: public football fans, mostly on phones before a matchday. Job: see the next fixtures' chances at a glance, open one to understand why.
Content: real model output from web/public/data/*.json. Constraints: no crests, no odds, no tips; club colours from config/kit_colours.csv.
Direction chosen in a structured-question round (decision page not served): "Kit room".
Unresolved: none.

## Direction contract

THESIS: A forecast you read like a team sheet: every probability wears the clubs' own shirt colours. Refuses the dark neon betting-dashboard and grey card-stack sports app.
OWN-WORLD: Home kit (light): cool shirt-white ground, navy ink, collar-band navy header with a three-stripe trim (gold, sky, white). Away kit (dark): deep navy ground, white ink, same trim. Club colours only inside data. Squad-number numerals (Big Shoulders Display) for every probability; Archivo for text. Hairline rules, fixed-scale rows.
STORY: Fan lands on this matchday's fixtures, sees who is favoured by how much, opens a match for scorelines, xG, goals and form in plain words, and can check the model's honest track record.
FIRST VIEWPORT: Navy collar-band header (wordmark left, tabs: Matches, Ratings, Track record, How it works; kit toggle right). Below: league filter chips + team search. Then day groups; each fixture a fixed-height row: time, home name, the kit-stripe bar (home colour / draw grey / away colour, split by probability), away name, and three squad-number percentages under it. Desktop: two-column grid of rows; detail opens as a side sheet. Mobile: single column, detail full-screen.
FORM: Kit design, position 6 of 7 on the ordered list (pools coupon, matchday programme, Ceefax pages, scoreboard, Panini album, kit design, pitch markings). seed:1f77e5d4ae2c646d. Raises: fixed-scale plates on one baseline (from botanical folio); hairline border density (from Japanese high-density); hard home/away halves mirrored (from cassette j-card). Signature move: kit-stripe probability bar with kit-clash rule (away side switches to its second colour when colours clash).
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
