import { Search, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import MatchDetail from '../components/MatchDetail.jsx';
import { FixtureRow, ResultRow } from '../components/MatchRow.jsx';
import { Empty, ErrorState, Loading } from '../components/State.jsx';
import { LEAGUE_ORDER, LEAGUE_SHORT, fmtShort, fmtStamp, groupByDay, useData } from '../lib/data.js';
import { href } from '../lib/router.js';

function useWide(query = '(min-width: 1080px)') {
  const [wide, setWide] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setWide(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, [query]);
  return wide;
}

function readFilter() {
  try {
    return localStorage.getItem('xg-league') || 'all';
  } catch {
    return 'all';
  }
}

function Filters({ leagues, league, setLeague, query, setQuery }) {
  return (
    <div className="filters">
      <div className="chips" role="group" aria-label="Competition">
        {['all', ...leagues].map((lg) => (
          <button
            key={lg}
            type="button"
            className="chipbtn"
            aria-pressed={league === lg}
            onClick={() => setLeague(lg)}
          >
            {lg === 'all' ? 'All' : LEAGUE_SHORT[lg]}
          </button>
        ))}
      </div>
      <label className="search">
        <Search aria-hidden="true" size={16} />
        <span className="sr-only">Find a team</span>
        <input
          type="search"
          placeholder="Find a team"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoComplete="off"
        />
        {query && (
          <button type="button" className="search__clear" onClick={() => setQuery('')} aria-label="Clear search">
            <X aria-hidden="true" size={14} />
          </button>
        )}
      </label>
    </div>
  );
}

const norm = (s) =>
  s
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

export default function Matches({ page, id }) {
  const { data, error, retry } = useData('predictions');
  const wide = useWide();
  const [league, setLeagueState] = useState(readFilter);
  const [query, setQuery] = useState('');
  const showResults = page === 'results';

  const setLeague = (lg) => {
    setLeagueState(lg);
    try {
      localStorage.setItem('xg-league', lg);
    } catch {
      /* private mode: keep it in memory only */
    }
  };

  const leagues = useMemo(
    () => (data ? LEAGUE_ORDER.filter((lg) => lg in data.leagues) : []),
    [data],
  );
  const activeLeague = league !== 'all' && !leagues.includes(league) ? 'all' : league;

  const filter = (list) => {
    const q = norm(query.trim());
    return list.filter(
      (m) =>
        (activeLeague === 'all' || m.league === activeLeague) &&
        (!q || norm(`${m.home.name} ${m.away.name} ${m.home.short} ${m.away.short}`).includes(q)),
    );
  };

  if (error) return <ErrorState error={error} retry={retry} />;
  if (!data) return <Loading rows={6} />;

  const selected = id ? data.matches.find((m) => String(m.id) === id) : null;

  // Phone: a match is its own screen.
  if (page === 'match' && !wide) {
    return selected ? (
      <MatchDetail m={selected} />
    ) : (
      <Empty title="This match isn’t in the current forecasts.">
        It may have kicked off already. <a href={href('/')}>See all matches</a>.
      </Empty>
    );
  }

  const list = filter(showResults ? data.recent : data.matches);
  const groups = groupByDay(list);
  const current = selected || (wide && !showResults ? list[0] : null);
  const split = wide && !showResults; // results read best full width; nothing to open beside them

  return (
    <div className={`workspace${split ? ' workspace--split' : ''}${showResults ? ' workspace--results' : ''}`}>
      <section className="board" aria-labelledby="board-h">
        <div className="board__head">
          <h1 id="board-h">{showResults ? 'Recent results' : 'Upcoming matches'}</h1>
          <p className="board__stamp">
            Updated {fmtStamp(data.generated_at)} · results up to {fmtShort(`${data.data_through}T12:00:00`)}
          </p>
        </div>
        <div className="segmented" role="tablist" aria-label="Show">
          <a role="tab" aria-selected={!showResults} href={href('/')}>
            Upcoming <span className="count">{data.matches.length}</span>
          </a>
          <a role="tab" aria-selected={showResults} href={href('/results')}>
            Results <span className="count">{data.recent.length}</span>
          </a>
        </div>
        <Filters leagues={leagues} league={activeLeague} setLeague={setLeague} query={query} setQuery={setQuery} />

        {groups.length === 0 ? (
          <Empty title={query ? `No matches for “${query}”.` : 'Nothing here right now.'}>
            {query || activeLeague !== 'all'
              ? 'Try another team or competition.'
              : showResults
                ? 'No covered matches in the last three weeks.'
                : 'No covered fixtures in the next three weeks (international break?).'}
          </Empty>
        ) : (
          groups.map((g) => (
            <section key={g.key} className="day" aria-labelledby={`d-${g.key}`}>
              <h2 id={`d-${g.key}`} className="day__h">
                {g.label}
                {g.label !== g.date && <span className="day__date">{g.date}</span>}
              </h2>
              <div className="day__rows">
                {g.matches.map((m) =>
                  showResults ? (
                    <ResultRow key={m.id} m={m} showLeague={activeLeague === 'all'} />
                  ) : (
                    <FixtureRow key={m.id} m={m} selected={current?.id === m.id} showLeague={activeLeague === 'all'} />
                  ),
                )}
              </div>
            </section>
          ))
        )}
      </section>

      {split && (
        <aside className="pane" aria-label="Match detail">
          {current ? <MatchDetail key={current.id} m={current} /> : <Empty title="Pick a match to see its forecast." />}
        </aside>
      )}
    </div>
  );
}
