// Plain-words explanations, shared so the same stat is explained the same way
// everywhere on the site.

export const EXPLAIN = {
  chances:
    'How likely each result is. Two models turn every result we have into team strengths, then estimate this match; when bookmakers have published odds, those are blended in too. The three numbers always add up to 100%.',
  kitBar:
    'The bar splits 100% between a home win (home club’s colours, left), a draw (grey, middle) and an away win (away club’s colours, right). The longer the section, the likelier that result.',
  hero: 'The big number is the single most likely result. The smaller two are the other outcomes.',
  odds:
    'This forecast also uses the betting market’s pre-match odds, which react to injuries and team news our models can’t see. Bookmakers usually publish them a few days before kickoff.',
  lowData:
    'At least one team has played few matches we can see recently (a newly promoted side, or a club from a league we don’t track), so this forecast leans more on assumptions.',
  replay:
    'This forecast wasn’t published live: we rebuilt it afterwards by replaying the season match by match, using only results from before kickoff, exactly as the live model works.',
  calledIt: '“Called it” means the result we rated most likely is what happened. “Missed” means something else happened.',
  xg: 'Expected goals (xG): how many goals each side would score on average if this match were played many times. 1.6 means “somewhere around one or two”, not a predicted score.',
  scoreBars: 'Each bar is scaled to the likeliest score (the longest bar). The percentage is that exact score’s chance after 90 minutes.',
  scoreGrid:
    'Each square is the chance (%) of that exact score after 90 minutes. Rows are home goals, columns are away goals. Darker squares are more likely.',
  over25: 'The chance of three or more goals in the match, counting both teams.',
  btts: 'The chance that both teams score at least once.',
  cleanSheet: 'The chance this team doesn’t concede a goal.',
  form: 'Last five results we have for this team in the competitions we track, oldest on the left, newest on the right.',
  changeColours:
    'Both clubs’ first-choice colours are too similar to tell apart, so the away side is shown in its second colour, as it would change kit on matchday.',
  confidence:
    'How much recent data backs both teams’ ratings. High: plenty of recent matches. Low: one side has played few matches we can see.',

  soFar: 'Goals (or assists, or clean sheets) so far this season in this competition.',
  projection:
    'Solid part: so far. Lighter part: what we expect from the remaining fixtures; the number at its end is the projected season total. The thin line underneath is the likely range: 8 in 10 simulated seasons finish inside it.',
  goldenBoot:
    'The chance this player ends the season as the competition’s top scorer, from 20,000 simulated rest-of-seasons. If players tie, they share the win.',
  topAssister: 'The chance this player ends the season with the most assists, from 20,000 simulated rest-of-seasons.',
  mostCleanSheets: 'The chance this team ends the season with the most clean sheets, from 20,000 simulated rest-of-seasons.',

  rating:
    'Goal edge: how many goals per match this team would beat an average Champions League side by, on a neutral ground. +1.00 means a one-goal-a-game edge; below zero means weaker than an average Champions League side.',
  ratingBar: 'Right of the centre line: better than an average Champions League side. Left: weaker. Longer is a bigger gap.',
  goalsFor: 'Goals this team would expect to score per match against an average Champions League side. Higher is better.',
  goalsAgainst: 'Goals this team would expect to concede per match against an average Champions League side. Lower is better.',

  logLoss:
    'Log loss scores how good the percentages were, not just whether the favourite won. Lower is better. It punishes confident wrong calls hardest. Guessing a third for each result scores 1.099; bookmakers’ closing odds score about 0.96.',
  brier:
    'Brier score: the average squared gap between our percentages and what happened (100% for the actual result, 0% for the others). Lower is better; 0 is perfect.',
  favouriteWon: 'How often the result we rated most likely actually happened.',
  avgChance: 'On average, the chance we had given to the result that actually happened. Higher is better.',
  settled: 'Forecasts whose match has been played, so we can check them.',
  calibration:
    'Every forecast grouped by the chance we gave it (across) against how often that outcome happened (up). If our 60% calls happen 60% of the time, the dot sits on the dashed “perfect” line.',
  byLeague: 'All numbers are log loss: lower is better. xGenius is what the site publishes; Stats only leaves out betting odds.',
};
