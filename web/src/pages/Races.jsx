import { useState } from 'react';
import ScrollRow from '../components/ScrollRow.jsx';
import Shirt from '../components/Shirt.jsx';
import Tip from '../components/Tip.jsx';
import { EXPLAIN } from '../lib/explain.js';
import { Empty, ErrorState, Loading } from '../components/State.jsx';
import { LEAGUE_ORDER, fmtStamp, useData } from '../lib/data.js';
import { luminance } from '../lib/kit.js';

const clubColour = (kit) => (kit ? (luminance(kit[0]) > 0.75 ? kit[1] : kit[0]) : 'var(--ink-2)');

/** Solid: so far. Lighter: the rest of the season, ending at the projected
 *  total (solid tick + number). Soft shaded band: the likely range, labelled
 *  directly underneath. */
function RaceBar({ now, projected, range, max, kit, unit }) {
  const pc = (v) => `${Math.min(100, (v / max) * 100)}%`;
  return (
    <span
      className="racebar"
      style={{ '--club': clubColour(kit) }}
      role="img"
      aria-label={`${now} so far, projected ${Math.round(projected)} ${unit}, likely ${range[0]} to ${range[1]}`}
    >
      <span className="racebar__track">
        <span className="racebar__proj" style={{ width: pc(projected) }} />
        <span className="racebar__now" style={{ width: pc(now) }} />
      </span>
      <span
        className="racebar__band"
        style={{ left: pc(range[0]), width: `calc(${pc(range[1])} - ${pc(range[0])})` }}
      />
      <span className="racebar__tick" style={{ left: pc(projected) }} />
      <span className="racebar__label" style={{ left: pc(projected) }}>
        {Math.round(projected)}
      </span>
      <span className="race__rangelabel" style={{ left: pc(range[0]) }}>
        likely {range[0]}–{range[1]}
      </span>
    </span>
  );
}

/** One-line key above each table. */
function RaceKey() {
  return (
    <p className="racekey">
      <span className="racekey__item">
        <span className="racekey__sw racekey__sw--now" aria-hidden="true" /> So far
      </span>
      <span className="racekey__item">
        <span className="racekey__sw racekey__sw--proj" aria-hidden="true" /> Projected (tick + number)
      </span>
      <span className="racekey__item">
        <span className="racekey__sw racekey__sw--band" aria-hidden="true" /> Likely range
      </span>
      <Tip text={EXPLAIN.projection} label="the bars" />
    </p>
  );
}

function pctLabel(p) {
  return p >= 0.995 ? '>99%' : p < 0.005 ? '<1%' : `${Math.round(p * 100)}%`;
}

function RaceTable({ rows, stat, unit, who, chance, chanceTip }) {
  if (!rows.length) return <Empty title="No data yet for this race." />;
  const max = Math.max(...rows.map((r) => r.range[1]), 1) * 1.04;
  return (
    <>
    <RaceKey />
    <div className="table-wrap">
      <table className="table race">
        <thead>
          <tr>
            <th scope="col" className="num">#</th>
            <th scope="col">{who}</th>
            <th scope="col" className="num">
              <Tip text={EXPLAIN.soFar} label="so far">
                So far
              </Tip>
            </th>
            <th scope="col">
              <Tip text={EXPLAIN.projection} label="the projection">
                Season projection
              </Tip>
            </th>
            <th scope="col" className="num race__chance-h">
              <Tip text={chanceTip} label={`${chance} chance`}>
                {chance} chance
              </Tip>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const name = r.player || r.team.name;
            return (
              <tr key={`${name}-${r.team.id}`}>
                <td className="num rank">{i + 1}</td>
                <th scope="row">
                  <span className="teamcell">
                    <Shirt kit={r.team.kit} size={18} />
                    <span>
                      {name}
                      <span className="teamcell__league teamcell__league--always">
                        {r.player ? r.team.short : `${r.played} played · ${r.remaining} to go`}
                      </span>
                    </span>
                  </span>
                </th>
                <td className="num race__now">{r[stat]}</td>
                <td className="race__barcol">
                  <RaceBar now={r[stat]} projected={r.projected} range={r.range} max={max} kit={r.team.kit} unit={unit} />
                </td>
                <td className="num race__chance">{pctLabel(r.p_top)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    </>
  );
}

export default function Races() {
  const { data, error, retry } = useData('races');
  const [league, setLeague] = useState(() => {
    try {
      return localStorage.getItem('xg-race') || 'premier_league';
    } catch {
      return 'premier_league';
    }
  });

  if (error) return <ErrorState error={error} retry={retry} what="the season races" />;
  if (!data) return <Loading rows={6} label="Loading season races" />;

  const comps = [...data.competitions].sort((a, b) => LEAGUE_ORDER.indexOf(a.league) - LEAGUE_ORDER.indexOf(b.league));
  const c = comps.find((x) => x.league === league) || comps[0];
  if (!c) return <Empty title="No season races to show yet." />;
  const choose = (lg) => {
    setLeague(lg);
    try {
      localStorage.setItem('xg-race', lg);
    } catch {
      /* in-memory only */
    }
  };
  const isCL = c.league === 'champions_league';

  return (
    <div className="page">
      <header className="page__head">
        <h1>Season races</h1>
        <p className="lede">
          Who finishes the season with the most goals, assists and clean sheets? Each projection is the total so far
          plus what the model expects from every remaining fixture, simulated 20,000 times.
        </p>
        <p className="board__stamp">
          Updated {fmtStamp(data.generated_at)} · {c.remaining_fixtures} {c.name} fixtures still to play
        </p>
      </header>

      <ScrollRow label="Competition" className="chips">
        {comps.map((x) => (
          <button key={x.league} type="button" className="chipbtn" aria-pressed={x.league === c.league} onClick={() => choose(x.league)}>
            {x.name}
          </button>
        ))}
      </ScrollRow>

      {isCL && (
        <p className="notice notice--inline">
          Champions League projections only count fixtures already scheduled. Knockout rounds join once they’re drawn,
          so totals for clubs that go deep will rise.
        </p>
      )}

      <section className="panel" aria-labelledby="g-h">
        <h2 id="g-h">Top scorers</h2>
        <RaceTable rows={c.scorers} stat="goals" unit="goals" who="Player" chance="Golden Boot" chanceTip={EXPLAIN.goldenBoot} />
        <p className="panel__note">
          <strong>Assumes every player stays fit and keeps their role.</strong> A player keeps their share of their
          team’s goals so far (eased back a little for small samples), applied to the goals the model expects the team
          to score from here. The data has no minutes or injury news, so an injured or dropped player is projected as
          if they’ll play every game, and a mid-season transfer is measured against their new club’s goals.
        </p>
      </section>

      <section className="panel" aria-labelledby="a-h">
        <h2 id="a-h">Top assists</h2>
        <RaceTable rows={c.assists} stat="assists" unit="assists" who="Player" chance="Top assister" chanceTip={EXPLAIN.topAssister} />
        <p className="panel__note">
          <strong>Assumes they stay fit. Incomplete list:</strong> our data only includes players who have scored at
          least once, so creators who haven’t scored yet are missing.
        </p>
      </section>

      <section className="panel" aria-labelledby="cs-h">
        <h2 id="cs-h">Clean sheets</h2>
        <RaceTable rows={c.clean_sheets} stat="cs" unit="clean sheets" who="Team" chance="Most clean sheets" chanceTip={EXPLAIN.mostCleanSheets} />
        <p className="panel__note">
          By team, not goalkeeper (we don’t have lineups). Each remaining match adds the model’s chance that the
          opponent doesn’t score. Tested on last season from this point: off by about 2 clean sheets per team over the
          rest of the season, against 3.3 for simply extending each team’s pace.
        </p>
      </section>

      <p className="panel__note page__source">
        Player goals, assists and appearances: football-data.org’s top-100 scorer list for each competition, refreshed
        every 6 hours. Team results and fixtures: football-data.co.uk and football-data.org.
      </p>
    </div>
  );
}
