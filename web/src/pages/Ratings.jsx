import { ArrowDown, ArrowUp, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import Shirt from '../components/Shirt.jsx';
import { ErrorState, Empty, Loading } from '../components/State.jsx';
import { fmtStamp, useData } from '../lib/data.js';

const COLS = [
  { key: 'rank', label: 'Rank', numeric: true, asc: true },
  { key: 'name', label: 'Team', asc: true },
  { key: 'league_name', label: 'League', asc: true, hide: 'sm' },
  { key: 'rating', label: 'Rating', numeric: true, title: 'Expected goal difference per match against an average Champions League side' },
  { key: 'xg_for', label: 'Attack', numeric: true, hide: 'sm', title: 'Expected goals scored against an average Champions League side' },
  { key: 'xg_against', label: 'Defence', numeric: true, asc: true, hide: 'sm', title: 'Expected goals conceded against an average Champions League side (lower is better)' },
];

const PAGE = 60;

const norm = (s) =>
  (s || '')
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

export default function Ratings() {
  const { data, error, retry } = useData('ratings');
  const [sort, setSort] = useState({ key: 'rank', asc: true });
  const [league, setLeague] = useState('all');
  const [query, setQuery] = useState('');
  const [all, setAll] = useState(false);

  const leagues = useMemo(
    () => (data ? [...new Set(data.teams.map((t) => t.league_name))].sort() : []),
    [data],
  );

  if (error) return <ErrorState error={error} retry={retry} what="the ratings" />;
  if (!data) return <Loading rows={8} label="Loading ratings" />;

  const q = norm(query.trim());
  const rows = data.teams
    .filter((t) => (league === 'all' || t.league_name === league) && (!q || norm(t.name).includes(q)))
    .sort((a, b) => {
      const x = a[sort.key];
      const y = b[sort.key];
      const c = typeof x === 'string' ? x.localeCompare(y) : x - y;
      return sort.asc ? c : -c;
    });
  const shown = all || q || league !== 'all' ? rows : rows.slice(0, PAGE);
  const best = Math.max(...data.teams.map((t) => t.rating));
  const worst = Math.min(...data.teams.map((t) => t.rating));

  const onSort = (col) =>
    setSort((s) => (s.key === col.key ? { key: col.key, asc: !s.asc } : { key: col.key, asc: !!col.asc }));

  return (
    <div className="page">
      <header className="page__head">
        <h1>Power ratings</h1>
        <p className="lede">
          Every club we track on one scale, across leagues. The rating is the goal difference a team would expect per
          match against an average Champions League side on a neutral ground. Champions League results are what let us
          compare leagues with each other.
        </p>
        <p className="board__stamp">Updated {fmtStamp(data.generated_at)}</p>
      </header>

      <div className="filters">
        <label className="select">
          <span className="sr-only">League</span>
          <select value={league} onChange={(e) => setLeague(e.target.value)}>
            <option value="all">All leagues</option>
            {leagues.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="search">
          <Search aria-hidden="true" size={16} />
          <span className="sr-only">Find a team</span>
          <input type="search" placeholder="Find a team" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
      </div>

      {shown.length === 0 ? (
        <Empty title={`No teams match “${query}”.`} />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                {COLS.map((c) => (
                  <th
                    key={c.key}
                    scope="col"
                    className={`${c.numeric ? 'num' : ''} ${c.hide ? `hide-${c.hide}` : ''}`}
                    aria-sort={sort.key === c.key ? (sort.asc ? 'ascending' : 'descending') : 'none'}
                  >
                    <button type="button" className="th-btn" onClick={() => onSort(c)} title={c.title}>
                      {c.label}
                      {sort.key === c.key &&
                        (sort.asc ? <ArrowUp aria-hidden="true" size={13} /> : <ArrowDown aria-hidden="true" size={13} />)}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.map((t) => (
                <tr key={t.id}>
                  <td className="num rank">{t.rank}</td>
                  <td>
                    <span className="teamcell">
                      <Shirt kit={t.kit} size={18} />
                      <span>
                        {t.name}
                        <span className="teamcell__league">{t.league_name}</span>
                      </span>
                    </span>
                  </td>
                  <td className="hide-sm muted">{t.league_name}</td>
                  <td className="num">
                    <span className="ratingcell">
                      <span className="ratingcell__bar" aria-hidden="true">
                        <span
                          className={t.rating >= 0 ? 'pos' : 'neg'}
                          style={{
                            width: `${(Math.abs(t.rating) / Math.max(best, -worst)) * 50}%`,
                          }}
                        />
                      </span>
                      <span className="ratingcell__n">
                        {t.rating > 0 ? '+' : t.rating < 0 ? '−' : ''}
                        {Math.abs(t.rating).toFixed(2)}
                      </span>
                    </span>
                  </td>
                  <td className="num hide-sm">{t.xg_for.toFixed(2)}</td>
                  <td className="num hide-sm">{t.xg_against.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!all && !q && league === 'all' && rows.length > PAGE && (
        <button type="button" className="btn btn--wide" onClick={() => setAll(true)}>
          Show all {rows.length} teams
        </button>
      )}
      <p className="panel__note">
        Ratings weigh recent matches most (a match from 10 months ago counts half as much as one from last week).
        Teams with very few recent matches are left out.
      </p>
    </div>
  );
}
