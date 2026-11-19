import { ArrowLeft } from 'lucide-react';
import { LEAGUE_SHORT, OUTCOME, dayOf, favourite, fmtShort, fmtTime, pct, pctNum, verdict } from '../lib/data.js';
import { distance, fixtureKits, inkOn, luminance } from '../lib/kit.js';
import { href } from '../lib/router.js';
import KitBar from './KitBar.jsx';
import Shirt from './Shirt.jsx';
import Tip from './Tip.jsx';
import { EXPLAIN } from '../lib/explain.js';

const CONFIDENCE = {
  high: 'Plenty of recent matches behind both teams’ ratings.',
  medium: 'A fair amount of recent data; treat the edges with some caution.',
  low: 'At least one team has played few matches we can see recently (e.g. a newly promoted side or a club from a league we don’t track), so this forecast leans on assumptions.',
};


function ScoreGrid({ m, kits }) {
  const max = Math.max(...m.grid.flat());
  // A white or near-white shirt can't tint a cell on a light page: use its trim colour instead.
  const tint = (kit) => (luminance(kit[0]) > 0.75 ? kit[1] : kit[0]);
  const homeTint = tint(kits.home);
  // Same kit-clash rule as the bar: if the two tints are hard to tell apart, the away side changes colour.
  const awayTint = [tint(kits.away), ...kits.away, '#4A5A80'].find(
    (c) => luminance(c) <= 0.75 && distance(c, homeTint) >= 150,
  );
  const colour = (i, j) => (i > j ? homeTint : i < j ? awayTint : null);
  return (
    <figure className="grid-fig">
      <table className="scoregrid">
        <caption className="sr-only">
          Chance of each exact score. Rows: {m.home.name} goals; columns: {m.away.name} goals.
        </caption>
        <thead>
          <tr>
            <th scope="col" className="scoregrid__corner">
              <span>{m.home.short}</span>
              <span>{m.away.short}</span>
            </th>
            {m.grid[0].map((_, j) => (
              <th key={j} scope="col">
                {j}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {m.grid.map((row, i) => (
            <tr key={i}>
              <th scope="row">{i}</th>
              {row.map((p, j) => {
                const c = colour(i, j);
                const a = Math.min(1, p / max);
                const strong = a > 0.55;
                const style = c
                  ? { background: `color-mix(in srgb, ${c} ${Math.round(8 + a * 82)}%, var(--surface))`, color: strong ? inkOn(c) : undefined }
                  : { background: `color-mix(in srgb, var(--draw) ${Math.round(10 + a * 80)}%, var(--surface))` };
                return (
                  <td key={j} style={style} aria-label={`${i}–${j}: ${(p * 100).toFixed(1)}%`}>
                    {p >= 0.01 ? Math.round(p * 100) : p >= 0.005 ? <span className="scoregrid__tiny">&lt;1</span> : ''}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <figcaption className="gridkey">
        <span className="gridkey__item">
          <span className="gridkey__sw" style={{ background: homeTint }} aria-hidden="true" /> {m.home.short} win
        </span>
        <span className="gridkey__item">
          <span className="gridkey__sw gridkey__sw--draw" aria-hidden="true" /> Draw
        </span>
        <span className="gridkey__item">
          <span className="gridkey__sw" style={{ background: awayTint }} aria-hidden="true" /> {m.away.short} win
        </span>
        <span className="gridkey__item gridkey__note">Darker = more likely · numbers are % chance</span>
        <Tip text={EXPLAIN.scoreGrid} label="the score grid" />
      </figcaption>
    </figure>
  );
}

function Meter({ label, value, hint, tip }) {
  return (
    <div className="meter">
      <div className="meter__row">
        <span className="meter__label">{tip ? <Tip text={tip} label={label}>{label}</Tip> : label}</span>
        <span className="meter__value">{pct(value)}</span>
      </div>
      <div className="meter__track" aria-hidden="true">
        <span style={{ width: `${value * 100}%` }} />
      </div>
      {hint && <p className="meter__hint">{hint}</p>}
    </div>
  );
}

function Form({ team, games }) {
  if (!games?.length) return <p className="muted">No recent matches in our data.</p>;
  return (
    <div className="form">
      <ol className="form__chips" aria-label={`${team} last ${games.length} results, oldest first`}>
        {games.map((g, i) => (
          <li key={i} className={`chip chip--${g.res}`} title={`${g.res} ${g.gf}–${g.ga} ${g.home ? 'v' : 'at'} ${g.opp}`}>
            <span aria-hidden="true">{g.res}</span>
            <span className="sr-only">
              {g.res === 'W' ? 'Won' : g.res === 'D' ? 'Drew' : 'Lost'} {g.gf}–{g.ga} {g.home ? 'v' : 'at'} {g.opp}
            </span>
          </li>
        ))}
      </ol>
      <ul className="form__list" aria-label="Most recent three">
        {[...games].reverse().slice(0, 3).map((g, i) => (
          <li key={i}>
            <span className={`res res--${g.res}`}>{g.gf}–{g.ga}</span> {g.home ? 'v' : 'at'} {g.opp}
            <span className="muted"> · {fmtShort(g.date)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function MatchDetail({ m, backHref = href('/') }) {
  const kits = fixtureKits(m.home, m.away);
  const fav = favourite(m.p);
  const day = dayOf(m.kickoff);
  const [xh, xa] = m.xg;
  return (
    <article className="detail" aria-labelledby="detail-title">
      <a className="detail__back" href={backHref}>
        <ArrowLeft aria-hidden="true" size={16} /> All matches
      </a>

      <p className="detail__when">
        {LEAGUE_SHORT[m.league]}
        {m.stage ? ` · ${m.stage}` : ''} · {day.label === day.date ? day.date : `${day.label}, ${day.date}`} ·{' '}
        <time dateTime={m.kickoff}>{fmtTime(m.kickoff)}</time>
      </p>

      <h1 id="detail-title" className="halves">
        <span className="halves__side">
          <Shirt kit={kits.home} size={40} className="halves__shirt" />
          <span className="halves__name">{m.home.name}</span>
          <span className="halves__role">Home</span>
        </span>
        <span className="sr-only"> v </span>
        <span className="halves__side halves__side--away">
          <Shirt kit={kits.away} size={40} className="halves__shirt" />
          <span className="halves__name">{m.away.name}</span>
          <span className="halves__role">
            Away
            {kits.changed && (
              <Tip text={EXPLAIN.changeColours} label="change colours">
                {' · change colours'}
              </Tip>
            )}
          </span>
        </span>
      </h1>

      <section className="detail__hero" aria-label="Result chances">
        <p className="detail__label">
          <Tip text={`${EXPLAIN.chances} ${EXPLAIN.kitBar}`} label="these chances">
            Chance of each result
          </Tip>
        </p>
        <KitBar p={m.p} kits={kits} size="large" />
        <div className="bignums">
          {m.p.map((x, i) => (
            <div key={i} className={`bignums__cell${i === fav ? ' bignums__cell--lead' : ''}`}>
              <span className="bignums__n">
                {pctNum(x)}
                <small>%</small>
              </span>
              <span className="bignums__label">
                {i === 0 ? `${m.home.short} win` : i === 2 ? `${m.away.short} win` : OUTCOME[1]}
              </span>
            </div>
          ))}
        </div>
        <p className="detail__verdict">{verdict(m)}</p>
      </section>

      <section className="panel" aria-labelledby="xg-h">
        <h2 id="xg-h">
          <Tip text={EXPLAIN.xg} label="expected goals">
            Expected goals
          </Tip>
        </h2>
        <div className="xg">
          <div className="xg__side">
            <span className="xg__n">{xh.toFixed(1)}</span>
            <span className="xg__team">{m.home.short}</span>
          </div>
          <div className="xg__side xg__side--away">
            <span className="xg__n">{xa.toFixed(1)}</span>
            <span className="xg__team">{m.away.short}</span>
          </div>
        </div>
        <p className="panel__note">
          The average number of goals each side would score if this match were played many times. Not a prediction of
          the score itself.
        </p>
      </section>

      <section className="panel" aria-labelledby="scores-h">
        <h2 id="scores-h">
          <Tip text={EXPLAIN.scoreBars} label="most likely scores">
            Most likely scores
          </Tip>
        </h2>
        <ol className="scores">
          {m.scores.map((s, i) => (
            <li key={i}>
              <span className="scores__score">
                {s.h}–{s.a}
              </span>
              <span className="scores__bar" aria-hidden="true">
                <span style={{ width: `${(s.p / m.scores[0].p) * 100}%` }} />
              </span>
              <span className="scores__p">{(s.p * 100).toFixed(1)}%</span>
            </li>
          ))}
        </ol>
        <p className="panel__note">
          Even the likeliest exact score comes up only about 1 time in {Math.round(1 / m.scores[0].p)}. Exact scores
          are hard to call.
        </p>
        <ScoreGrid m={m} kits={kits} />
      </section>

      <section className="panel" aria-labelledby="goals-h">
        <h2 id="goals-h">Goals</h2>
        <Meter label="Over 2.5 goals" value={m.over25} hint="Three or more goals in total." tip={EXPLAIN.over25} />
        <Meter label="Both teams score" value={m.btts} hint="Each side scores at least once." tip={EXPLAIN.btts} />
        <Meter label={`${m.home.short} keep a clean sheet`} value={m.clean_sheet[0]} tip={EXPLAIN.cleanSheet} />
        <Meter label={`${m.away.short} keep a clean sheet`} value={m.clean_sheet[1]} tip={EXPLAIN.cleanSheet} />
        <p className="panel__note">Each bar fills to its percentage.</p>
      </section>

      <section className="panel" aria-labelledby="form-h">
        <h2 id="form-h">
          <Tip text={EXPLAIN.form} label="recent form">
            Recent form
          </Tip>
        </h2>
        <p className="formkey" aria-hidden="true">
          <span className="chip chip--W">W</span> win <span className="chip chip--D">D</span> draw{' '}
          <span className="chip chip--L">L</span> loss · oldest → newest
        </p>
        <div className="form-pair">
          <div>
            <h3>{m.home.short}</h3>
            <Form team={m.home.short} games={m.form.home} />
          </div>
          <div>
            <h3>{m.away.short}</h3>
            <Form team={m.away.short} games={m.form.away} />
          </div>
        </div>
        <p className="panel__note">Last five matches in our data, all competitions we track. The list shows the most recent three.</p>
      </section>

      <section className={`panel panel--confidence panel--${m.confidence}`} aria-labelledby="conf-h">
        <h2 id="conf-h">
          <Tip text={EXPLAIN.confidence} label="confidence">
            How sure is this?
          </Tip>
        </h2>
        <p>
          <strong className="conf">{m.confidence[0].toUpperCase() + m.confidence.slice(1)} data confidence.</strong>{' '}
          {CONFIDENCE[m.confidence]}
        </p>
        <p>
          {m.market
            ? 'This forecast blends our models with the betting market’s pre-match odds, which carry news we can’t see (injuries, team news). That makes it more accurate.'
            : m.league === 'champions_league'
              ? 'Pure statistics: no betting odds are available to us for Champions League matches.'
              : 'Pure statistics for now. Once bookmakers’ odds for this match are published (usually a few days before kickoff), they’re blended in.'}
        </p>
        <p className="panel__note">
          Probabilities, not certainties: a 70% favourite still fails to win 3 times in 10. <a href={href('/record')}>See how accurate the model has been.</a>
        </p>
      </section>
    </article>
  );
}
