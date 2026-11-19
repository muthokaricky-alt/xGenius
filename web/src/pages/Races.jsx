import { useState } from 'react';
import { Empty, ErrorState, Loading } from '../components/State.jsx';
import { LEAGUE_ORDER, fmtStamp, useData } from '../lib/data.js';
import { luminance } from '../lib/kit.js';

/** Current total in the club's colour, projected rest of season as a lighter
 *  extension, and the likely range (10th–90th percentile) as a whisker. */
function RaceBar({ now, projected, range, max, kit }) {
  const pc = (v) => `${Math.min(100, (v / max) * 100)}%`;
  const main = kit ? (luminance(kit[0]) > 0.75 ? kit[1] : kit[0]) : 'var(--ink-2)';
  return (
    <span className="racebar" aria-hidden="true" style={{ '--club': main }}>
      <span className="racebar__proj" style={{ width: pc(projected) }} />
      <span className="racebar__now" style={{ width: pc(now) }} />
      <span className="racebar__range" style={{ left: pc(range[0]), width: `calc(${pc(range[1])} - ${pc(range[0])})` }} />
    </span>
  );
}

function Swatch({ kit }) {
  return (
    <span
      className="swatch swatch--sm"
      style={kit ? { '--main': kit[0], '--trim': kit[1] } : undefined}
      aria-hidden="true"
    />
  );
}

function RaceTable({ rows, stat, unit, who }) {
  if (!rows.length) return <Empty title="No data yet for this race." />;
  const max = Math.max(...rows.map((r) => r.range[1]), 1);
  return (
    <div className="table-wrap">
      <table className="table race">
        <thead>
          <tr>
            <th scope="col" className="num">#</th>
            <th scope="col">{who}</th>
            <th scope="col" className="num">Now</th>
            <th scope="col" className="race__barcol hide-sm">
              <span className="sr-only">Projection chart</span>
            </th>
            <th scope="col" className="num">Projected</th>
            <th scope="col" className="num" title="Chance of finishing the season top of this list (shared first place counts as a share)">
              Top
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
                    <Swatch kit={r.team.kit} />
                    <span>
                      {name}
                      {r.player && <span className="teamcell__league teamcell__league--always">{r.team.short}</span>}
                      {!r.player && (
                        <span className="teamcell__league teamcell__league--always">
                          {r.played} played · {r.remaining} to go
                        </span>
                      )}
                    </span>
                  </span>
                </th>
                <td className="num race__now">{r[stat]}</td>
                <td className="race__barcol hide-sm">
                  <RaceBar now={r[stat]} projected={r.projected} range={r.range} max={max} kit={r.team.kit} />
                </td>
                <td className="num">
                  <span className="race__proj">{Math.round(r.projected)}</span>
                  <span className="race__range" aria-label={`likely ${r.range[0]} to ${r.range[1]} ${unit}`}>
                    {r.range[0]}–{r.range[1]}
                  </span>
                </td>
                <td className="num race__top">{r.p_top >= 0.995 ? '>99%' : r.p_top < 0.005 ? '<1%' : `${Math.round(r.p_top * 100)}%`}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
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

      <div className="chips chips--page" role="group" aria-label="Competition">
        {comps.map((x) => (
          <button key={x.league} type="button" className="chipbtn" aria-pressed={x.league === c.league} onClick={() => choose(x.league)}>
            {x.name}
          </button>
        ))}
      </div>

      {isCL && (
        <p className="notice notice--inline">
          Champions League projections only count fixtures already scheduled. Knockout rounds join once they’re drawn,
          so totals for clubs that go deep will rise.
        </p>
      )}

      <section className="panel" aria-labelledby="g-h">
        <h2 id="g-h">Top scorers</h2>
        <RaceTable rows={c.scorers} stat="goals" unit="goals" who="Player" />
        <p className="panel__note">
          A player keeps their share of their team’s goals so far (eased back a little for small samples), applied to
          the goals the model expects the team to score from here. It can’t see minutes, injuries, suspensions,
          transfers or penalty duty.
        </p>
      </section>

      <section className="panel" aria-labelledby="a-h">
        <h2 id="a-h">Top assists</h2>
        <RaceTable rows={c.assists} stat="assists" unit="assists" who="Player" />
        <p className="panel__note">
          <strong>Incomplete list:</strong> our free data only includes players who have scored at least once, so
          creators who haven’t scored yet are missing.
        </p>
      </section>

      <section className="panel" aria-labelledby="cs-h">
        <h2 id="cs-h">Clean sheets</h2>
        <RaceTable rows={c.clean_sheets} stat="cs" unit="clean sheets" who="Team" />
        <p className="panel__note">
          By team, not goalkeeper (we don’t have lineups). Each remaining match adds the model’s chance that the
          opponent doesn’t score. Tested on last season from this point: the model was off by about 2 clean sheets
          per team over the rest of the season, against 3.3 for simply extending each team’s pace.
        </p>
      </section>

      <p className="panel__note">
        <strong>Now</strong>: so far this season. <strong>Projected</strong>: expected final total, with the likely
        range (8 in 10 simulated seasons land inside it). <strong>Top</strong>: chance of finishing first.
      </p>
    </div>
  );
}
