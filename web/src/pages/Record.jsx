import { ErrorState, Loading } from '../components/State.jsx';
import { LEAGUE_ORDER, LEAGUE_SHORT, favourite, fmtShort, logLoss, outcomeIndex, useData } from '../lib/data.js';
import { href } from '../lib/router.js';

function settle(matches) {
  const done = matches.filter((m) => m.result);
  const n = done.length;
  if (!n) return null;
  let hits = 0;
  let ll = 0;
  let given = 0;
  for (const m of done) {
    const y = outcomeIndex(m.result[0], m.result[1]);
    if (favourite(m.p) === y) hits += 1;
    ll += logLoss(m.p, y);
    given += m.p[y];
  }
  return { n, hit: hits / n, ll: ll / n, given: given / n, from: done[0].kickoff, to: done[n - 1].kickoff };
}

function Stat({ value, label }) {
  return (
    <div className="stat">
      <dd className="stat__v">{value}</dd>
      <dt className="stat__l">{label}</dt>
    </div>
  );
}

function Calibration({ points }) {
  const W = 320;
  const pad = 44;
  const s = (v) => pad + v * (W - pad * 1.5);
  const y = (v) => W - pad - v * (W - pad * 1.5);
  const maxN = Math.max(...points.map((p) => p.n));
  return (
    <figure className="calib">
      <svg viewBox={`0 0 ${W} ${W}`} role="img" aria-labelledby="calib-t">
        <title id="calib-t">
          Calibration: for each band of forecast probability, how often that outcome really happened.{' '}
          {points.map((p) => `Forecast ${Math.round(p.forecast * 100)}%, happened ${Math.round(p.observed * 100)}%`).join('; ')}.
        </title>
        {[0, 0.2, 0.4, 0.6, 0.8, 1].map((t) => (
          <g key={t}>
            <line x1={s(0)} x2={s(1)} y1={y(t)} y2={y(t)} className="calib__grid" />
            <text x={s(0) - 8} y={y(t) + 4} textAnchor="end" className="calib__tick">
              {t * 100}
            </text>
            <text x={s(t)} y={y(0) + 18} textAnchor="middle" className="calib__tick">
              {t * 100}
            </text>
          </g>
        ))}
        <line x1={s(0)} y1={y(0)} x2={s(1)} y2={y(1)} className="calib__ideal" />
        <text x={s(0.5)} y={W - 2} textAnchor="middle" className="calib__axis">
          We said (%)
        </text>
        <text x={10} y={y(0.5)} textAnchor="middle" className="calib__axis" transform={`rotate(-90 10 ${y(0.5)})`}>
          It happened (%)
        </text>
        <polyline className="calib__line" points={points.map((p) => `${s(p.forecast)},${y(p.observed)}`).join(' ')} />
        {points.map((p, i) => (
          <circle key={i} cx={s(p.forecast)} cy={y(p.observed)} r={3 + 5 * Math.sqrt(p.n / maxN)} className="calib__dot" />
        ))}
      </svg>
      <figcaption>
        Every forecast from the 2018–2026 test seasons, grouped by the chance we gave. A dot on the dashed line means
        that when we said 60%, it happened 60% of the time. Bigger dots stand for more forecasts.
      </figcaption>
    </figure>
  );
}

const llNote = 'Log loss: lower is better. It punishes confident wrong calls hardest. Guessing a third for each result scores 1.099.';

export default function Record() {
  const hist = useData('history');
  const perf = useData('performance');
  if (hist.error) return <ErrorState error={hist.error} retry={hist.retry} what="the track record" />;
  if (perf.error) return <ErrorState error={perf.error} retry={perf.retry} what="the backtest results" />;
  if (!hist.data || !perf.data) return <Loading rows={6} label="Loading track record" />;

  const live = settle(hist.data.matches.filter((m) => m.source === 'live'));
  const replay = settle(hist.data.matches.filter((m) => m.source === 'replay'));
  const pending = hist.data.matches.filter((m) => !m.result).length;
  const t = perf.data.test;
  const lb = t.leaderboard;
  const ens = lb.find((r) => r.key === 'ensemble');
  const mkt = lb.find((r) => r.key === 'market');
  const base = lb.find((r) => r.key === 'base_rate');
  const byLeague = [...t.by_league].sort(
    (a, b) => (LEAGUE_ORDER.indexOf(a.league) + 1 || 99) - (LEAGUE_ORDER.indexOf(b.league) + 1 || 99),
  );

  return (
    <div className="page">
      <header className="page__head">
        <h1>Track record</h1>
        <p className="lede">
          How the forecasts have held up, misses included. Every number here is out of sample: each forecast was made
          using only matches played before it.
        </p>
      </header>

      <section className="panel" aria-labelledby="season-h">
        <h2 id="season-h">This season</h2>
        {live ? (
          <>
            <h3>Published live</h3>
            <dl className="stats">
              <Stat value={live.n} label="forecasts settled" />
              <Stat value={`${Math.round(live.hit * 100)}%`} label="favourite won" />
              <Stat value={`${Math.round(live.given * 100)}%`} label="average chance we gave the actual result" />
              <Stat value={live.ll.toFixed(3)} label="log loss" />
            </dl>
          </>
        ) : (
          <p>
            The live record starts with this round: {pending} published forecasts are waiting for their results.
            Every forecast is frozen at kickoff and checked against the final score.
          </p>
        )}
        {replay && (
          <>
            <h3>
              Earlier this season, replayed{' '}
              <span className="muted">
                ({fmtShort(replay.from)} – {fmtShort(replay.to)})
              </span>
            </h3>
            <dl className="stats">
              <Stat value={replay.n} label="matches" />
              <Stat value={`${Math.round(replay.hit * 100)}%`} label="favourite won" />
              <Stat value={`${Math.round(replay.given * 100)}%`} label="average chance we gave the actual result" />
              <Stat value={replay.ll.toFixed(3)} label="log loss" />
            </dl>
            <p className="panel__note">
              Before the site went live we replayed the season match by match, refitting the model as results came in,
              exactly as it runs now. Covered matches only, which skew towards big clubs and are easier to call than
              an average league game. {llNote}
            </p>
          </>
        )}
        <p>
          <a href={href('/results')}>See recent results against our forecasts</a>
        </p>
      </section>

      <section className="panel" aria-labelledby="lb-h">
        <h2 id="lb-h">Eight seasons, {t.matches.toLocaleString()} matches</h2>
        <p>
          We tested the model on every match in {t.leagues} European leagues from {t.from.slice(0, 4)} to {t.to.slice(0, 4)},
          predicting each matchday using only what was known before it. The bookmakers’ closing odds are shown as a
          benchmark: they are still better than us, as they are better than almost every public model.
        </p>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col" className="num" title="Lower is better">Log loss</th>
                <th scope="col" className="num hide-sm" title="Lower is better">Brier</th>
                <th scope="col" className="num">Favourite won</th>
              </tr>
            </thead>
            <tbody>
              {lb.map((r) => (
                <tr key={r.key} className={r.key === 'ensemble' ? 'row--ours' : r.key === 'market' ? 'row--bench' : ''}>
                  <th scope="row">
                    {r.key === 'ensemble' ? 'xGenius (Elo + Dixon-Coles)' : r.model}
                    {r.key === 'market' && <span className="teamcell__league">Closing odds, benchmark only</span>}
                    {r.key === 'base_rate' && <span className="teamcell__league">League averages, ignores teams</span>}
                  </th>
                  <td className="num">{r.log_loss.toFixed(4)}</td>
                  <td className="num hide-sm">{r.brier.toFixed(4)}</td>
                  <td className="num">{(r.accuracy * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="panel__note">
          {llNote} We close {Math.round(((base.log_loss - ens.log_loss) / (base.log_loss - mkt.log_loss)) * 100)}% of the
          gap between knowing nothing about the teams and the betting market.
        </p>
      </section>

      <section className="panel" aria-labelledby="cal-h">
        <h2 id="cal-h">Do the percentages mean what they say?</h2>
        <Calibration points={t.calibration} />
      </section>

      <section className="panel" aria-labelledby="league-h">
        <h2 id="league-h">By league</h2>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">League</th>
                <th scope="col" className="num">xGenius</th>
                <th scope="col" className="num">Market</th>
                <th scope="col" className="num hide-sm">League averages</th>
              </tr>
            </thead>
            <tbody>
              {byLeague.map((r) => (
                <tr key={r.league}>
                  <th scope="row">{LEAGUE_SHORT[r.league] || r.league}</th>
                  <td className="num">{r.ensemble.toFixed(3)}</td>
                  <td className="num muted">{r.market.toFixed(3)}</td>
                  <td className="num muted hide-sm">{r.base_rate.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="panel__note">Log loss per league, 2018–2026. Lower is better.</p>
      </section>

      <section className="panel" aria-labelledby="cl-h">
        <h2 id="cl-h">Champions League</h2>
        <p>
          {perf.data.champions_league.matches} matches from {perf.data.champions_league.from.slice(0, 4)} to{' '}
          {perf.data.champions_league.to.slice(0, 4)}. Clubs from different leagues rarely meet, so these are the
          hardest forecasts to make: the model learns how strong each league is from these very matches.
        </p>
        <dl className="stats">
          {perf.data.champions_league.leaderboard.map((r) => (
            <Stat
              key={r.key}
              value={r.log_loss.toFixed(3)}
              label={`${r.key === 'ensemble' ? 'xGenius' : r.model} log loss (favourite won ${Math.round(r.accuracy * 100)}%)`}
            />
          ))}
        </dl>
      </section>
    </div>
  );
}
