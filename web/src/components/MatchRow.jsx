import { Check, X } from 'lucide-react';
import { LEAGUE_SHORT, OUTCOME, favourite, fmtShort, fmtTime, outcomeIndex, pct, pctNum } from '../lib/data.js';
import { fixtureKits } from '../lib/kit.js';
import { href } from '../lib/router.js';
import KitBar from './KitBar.jsx';

function Numbers({ p, highlight }) {
  return (
    <div className="nums" aria-hidden="true">
      {p.map((x, i) => (
        <span key={i} className={`nums__n${i === highlight ? ' nums__n--lead' : ''}`}>
          {pctNum(x)}
          <small>%</small>
        </span>
      ))}
    </div>
  );
}

function Competition({ m, showLeague }) {
  if (!showLeague && !m.stage) return null;
  return (
    <span className="fx__comp">
      {showLeague && LEAGUE_SHORT[m.league]}
      {showLeague && m.stage && ' · '}
      {m.stage}
    </span>
  );
}

export function FixtureRow({ m, selected, showLeague }) {
  const kits = fixtureKits(m.home, m.away);
  const fav = favourite(m.p);
  return (
    <a
      className="fx"
      href={href(`/match/${m.id}`)}
      aria-current={selected ? 'true' : undefined}
      aria-label={`${m.home.name} v ${m.away.name}, ${fmtTime(m.kickoff)}. ${OUTCOME.map(
        (o, i) => `${o} ${pct(m.p[i])}`,
      ).join(', ')}`}
    >
      <div className="fx__meta">
        <time dateTime={m.kickoff}>{fmtTime(m.kickoff)}</time>
        <Competition m={m} showLeague={showLeague} />
        {m.market && (
          <span className="tag" title="Blended with the betting market's pre-match odds">
            + odds
          </span>
        )}
        {m.confidence === 'low' && <span className="tag" title="Little recent data behind at least one team">Low data</span>}
      </div>
      <div className="fx__teams">
        <span className={`fx__team${fav === 0 ? ' fx__team--fav' : ''}`}>{m.home.short}</span>
        <span className="fx__v">v</span>
        <span className={`fx__team fx__team--away${fav === 2 ? ' fx__team--fav' : ''}`}>{m.away.short}</span>
      </div>
      <KitBar p={m.p} kits={kits} />
      <Numbers p={m.p} highlight={fav} />
    </a>
  );
}

export function ResultRow({ m, showLeague }) {
  const kits = fixtureKits(m.home, m.away);
  const [hg, ag] = m.result;
  const actual = outcomeIndex(hg, ag);
  const fav = favourite(m.p);
  const hit = actual === fav;
  return (
    <div className="fx fx--result">
      <div className="fx__meta">
        <time dateTime={m.kickoff}>{fmtShort(m.kickoff)}</time>
        <Competition m={m} showLeague={showLeague} />
        {m.source === 'replay' && (
          <span className="tag" title="Forecast reconstructed from the walk-forward backtest, made before the site went live">
            Replay
          </span>
        )}
      </div>
      <div className="fx__teams">
        <span className={`fx__team${actual === 0 ? ' fx__team--fav' : ''}`}>{m.home.short}</span>
        <span className="fx__score" aria-label={`final score ${hg} to ${ag}`}>
          {hg}–{ag}
        </span>
        <span className={`fx__team fx__team--away${actual === 2 ? ' fx__team--fav' : ''}`}>{m.away.short}</span>
      </div>
      <KitBar p={m.p} kits={kits} settle={false} />
      <div className={`verdict-line ${hit ? 'verdict-line--hit' : 'verdict-line--miss'}`}>
        {hit ? <Check aria-hidden="true" size={15} /> : <X aria-hidden="true" size={15} />}
        <span>
          {hit ? 'Called it' : 'Missed'}: we had{' '}
          {actual === 1 ? 'a draw' : `${actual === 0 ? m.home.short : m.away.short} to win`} at {pct(m.p[actual])}
        </span>
      </div>
    </div>
  );
}
