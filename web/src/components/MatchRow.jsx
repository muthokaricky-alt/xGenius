import { Check, X } from 'lucide-react';
import { LEAGUE_SHORT, OUTCOME, favourite, fmtShort, fmtTime, outcomeIndex, pct, pctNum } from '../lib/data.js';
import { fixtureKits } from '../lib/kit.js';
import { href } from '../lib/router.js';
import KitBar from './KitBar.jsx';
import Shirt from './Shirt.jsx';
import Tip from './Tip.jsx';
import { EXPLAIN } from '../lib/explain.js';

const LABELS = ['Home', 'Draw', 'Away'];

/** The most likely outcome is the hero; the other two step back. */
function Numbers({ p, lead }) {
  return (
    <div className="nums" aria-hidden="true">
      {p.map((x, i) => (
        <span key={i} className={`nums__n${i === lead ? ' nums__n--lead' : ''}`}>
          <span className="nums__v">
            {pctNum(x)}
            <small>%</small>
          </span>
          <span className="nums__l">{LABELS[i]}</span>
        </span>
      ))}
    </div>
  );
}

function Meta({ m, showLeague, children }) {
  return (
    <div className="fx__meta">
      {showLeague && <span className="fx__comp">{LEAGUE_SHORT[m.league]}</span>}
      {m.stage && <span className="fx__comp">{m.stage}</span>}
      {children}
    </div>
  );
}

function Team({ team, kit, away, strong }) {
  return (
    <span className={`fx__team${away ? ' fx__team--away' : ''}${strong ? ' fx__team--fav' : ''}`}>
      <Shirt kit={kit} size={17} />
      <span className="fx__name">{team.short}</span>
    </span>
  );
}

export function FixtureRow({ m, selected, showLeague }) {
  const kits = fixtureKits(m.home, m.away);
  const fav = favourite(m.p);
  return (
    <div className={`fx fx--link${selected ? ' fx--selected' : ''}`}>
      {/* The whole card is clickable through this link's ::after; the (i) buttons sit above it. */}
      <a
        className="fx__link"
        href={href(`/match/${m.id}`)}
        aria-current={selected ? 'true' : undefined}
        aria-label={`${m.home.name} v ${m.away.name}, ${fmtTime(m.kickoff)}. ${OUTCOME.map(
          (o, i) => `${o} ${pct(m.p[i])}`,
        ).join(', ')}`}
      />
      <Meta m={m} showLeague={showLeague}>
        {m.market && (
          <Tip text={EXPLAIN.odds} label="+ odds" className="tag">
            + odds
          </Tip>
        )}
        {m.confidence === 'low' && (
          <Tip text={EXPLAIN.lowData} label="low data" className="tag">
            Low data
          </Tip>
        )}
      </Meta>
      <div className="fx__teams">
        <Team team={m.home} kit={kits.home} strong={fav === 0} />
        <time className="fx__time" dateTime={m.kickoff}>
          {fmtTime(m.kickoff)}
        </time>
        <Team team={m.away} kit={kits.away} away strong={fav === 2} />
      </div>
      <KitBar p={m.p} kits={kits} />
      <Numbers p={m.p} lead={fav} />
    </div>
  );
}

export function ResultRow({ m, showLeague }) {
  const kits = fixtureKits(m.home, m.away);
  const [hg, ag] = m.result;
  const actual = outcomeIndex(hg, ag);
  const hit = actual === favourite(m.p);
  return (
    <div className="fx fx--result">
      <Meta m={m} showLeague={showLeague}>
        <time dateTime={m.kickoff}>{fmtShort(m.kickoff)}</time>
        {m.source === 'replay' && (
          <Tip text={EXPLAIN.replay} label="replay" className="tag">
            Replay
          </Tip>
        )}
      </Meta>
      <div className="fx__teams">
        <Team team={m.home} kit={kits.home} strong={actual === 0} />
        <span className="fx__score" aria-label={`final score ${hg} to ${ag}`}>
          {hg}–{ag}
        </span>
        <Team team={m.away} kit={kits.away} away strong={actual === 2} />
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
