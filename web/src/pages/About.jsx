import { href } from '../lib/router.js';

export default function About() {
  return (
    <div className="page page--prose">
      <header className="page__head">
        <h1>How it works</h1>
        <p className="lede">
          xGenius turns results into probabilities. Our models only know what the scorelines say about how good each
          team is; when bookmakers’ odds are out, they bring in what we can’t see, like injuries and team news.
        </p>
      </header>

      <section className="prose">
        <h2>What you’re looking at</h2>
        <p>
          For each match you get the chance of a home win, a draw and an away win. The coloured bar splits 100% between
          those three, in each club’s colours (if the shirts clash, the away side switches to its second colour, as it
          would on the pitch). A 60% favourite isn’t a sure thing: it should fail to win 4 times in 10.
        </p>
        <p>
          <strong>Expected goals (xG)</strong> is the average number of goals each side would score if the match were
          played many times. <strong>Most likely scores</strong> and the score grid show the chance of every exact
          result after 90 minutes, extra time excluded.
        </p>

        <h2>The models</h2>
        <p>Two models, combined:</p>
        <ul>
          <li>
            <strong>Elo ratings.</strong> Every team has a rating that goes up when it wins and down when it loses,
            more for bigger wins and for beating stronger teams.
          </li>
          <li>
            <strong>Dixon-Coles.</strong> A goals model: each team has an attacking and a defensive strength, recent
            matches count most, and home advantage is learned per league. It also tells us how likely each exact
            score is. This season it also learns from expected-goals data, which says how good a team’s chances were,
            not just whether they went in.
          </li>
        </ul>
        <ul>
          <li>
            <strong>The betting market.</strong> A few days before most league matches, bookmakers publish odds. Those
            prices react to injuries, suspensions and team news that our models never see, so when they’re available
            we blend them in. Matches that use them are marked “+ odds”. Champions League forecasts and anything
            further ahead are pure statistics.
          </li>
        </ul>
        <p>
          The blend’s weights are re-learned every season from forecasts the models made before seeing the results,
          and checked for calibration: when xGenius says 60%, that outcome should happen about 60% of the time.
        </p>

        <h2>Season races</h2>
        <p>
          The <a href={href('/races')}>races</a> page projects who finishes the season with the most goals, assists
          and clean sheets in each competition: the total so far plus what the model expects from each remaining
          fixture. A player’s share of their team’s goals blends this season with last season, so a slow start
          doesn’t sink a proven scorer. It’s still the weakest assumption on the site: it can’t see injuries, rotation
          or a new signing taking over.
        </p>

        <h2>Comparing leagues</h2>
        <p>
          A Premier League side and a Bundesliga side almost never play each other, so how do we compare them? Through
          the Champions League. Every European match tells the model a little about how strong each league is, which
          puts all the clubs on one scale. That’s what the <a href={href('/ratings')}>ratings</a> show, and why
          Champions League forecasts are the least certain we publish.
        </p>

        <h2>How we test it</h2>
        <p>
          We replayed eight seasons (2018–2026) of 15 leagues, about 32,000 matches, predicting each matchday using
          only matches played before it, then scored every forecast against what happened. The settings were tuned on
          two earlier seasons that the test never touches. The result, and how it compares with bookmakers, is on the{' '}
          <a href={href('/record')}>track record</a> page.
        </p>

        <h2>What it covers</h2>
        <p>
          Every Premier League and Champions League match, plus Bayern Munich, Borussia Dortmund, Juventus, Inter, AC
          Milan, Napoli, Roma, Lazio, Paris Saint-Germain, Barcelona, Real Madrid and Atlético Madrid in their leagues.
          Ratings come from 15 leagues, because those clubs’ opponents and Champions League rivals need ratings too.
          Forecasts update every six hours.
        </p>

        <h2>Data</h2>
        <p>
          Results and expected goals: <a href="https://www.football-data.co.uk" rel="noopener">football-data.co.uk</a>.
          Fixtures and Champions League results: <a href="https://www.football-data.org" rel="noopener">football-data.org</a>.
          Club names and colours are used to identify teams only; xGenius isn’t affiliated with any club or league.
        </p>

        <h2>Not betting advice</h2>
        <p>
          This is a statistics project. It uses market odds as information, but shows no odds, gives no tips and
          links to no bookmaker. No model can make betting a safe way to earn money. If gambling stops being fun, <a href="https://www.begambleaware.org" rel="noopener">BeGambleAware</a> can help.
        </p>
      </section>
    </div>
  );
}
