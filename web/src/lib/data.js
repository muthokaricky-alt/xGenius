import { useEffect, useState } from 'react';

const cache = new Map();

function load(name) {
  if (!cache.has(name)) {
    const url = `${import.meta.env.BASE_URL}data/${name}.json`;
    cache.set(
      name,
      fetch(url, { cache: 'no-cache' }).then((r) => {
        if (!r.ok) throw new Error(`${name}.json: HTTP ${r.status}`);
        return r.json();
      }),
    );
    cache.get(name).catch(() => cache.delete(name)); // allow a retry
  }
  return cache.get(name);
}

/** { data, error, retry } for one of the published JSON files. */
export function useData(name) {
  const [state, setState] = useState({ data: null, error: null });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let live = true;
    load(name).then(
      (data) => live && setState({ data, error: null }),
      (error) => live && setState({ data: null, error }),
    );
    return () => {
      live = false;
    };
  }, [name, attempt]);
  return { ...state, retry: () => setAttempt((a) => a + 1) };
}

export const pct = (p) => `${Math.round(p * 100)}%`;
export const pctNum = (p) => Math.round(p * 100);

const dayFmt = new Intl.DateTimeFormat(undefined, { weekday: 'long', day: 'numeric', month: 'long' });
const timeFmt = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' });
const shortFmt = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' });
const stampFmt = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

export const fmtTime = (iso) => timeFmt.format(new Date(iso));
export const fmtShort = (iso) => shortFmt.format(new Date(iso));
export const fmtStamp = (iso) => stampFmt.format(new Date(iso));

/** Local calendar key and a human label (Today, Tomorrow, or the date). */
export function dayOf(iso) {
  const d = new Date(iso);
  const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
  const today = new Date();
  const diff = Math.round(
    (new Date(d.getFullYear(), d.getMonth(), d.getDate()) -
      new Date(today.getFullYear(), today.getMonth(), today.getDate())) /
      86400000,
  );
  const label = diff === 0 ? 'Today' : diff === 1 ? 'Tomorrow' : diff === -1 ? 'Yesterday' : dayFmt.format(d);
  return { key, label, date: dayFmt.format(d) };
}

export function groupByDay(matches) {
  const groups = [];
  for (const m of matches) {
    const d = dayOf(m.kickoff);
    const last = groups[groups.length - 1];
    if (last && last.key === d.key) last.matches.push(m);
    else groups.push({ ...d, matches: [m] });
  }
  return groups;
}

export const OUTCOME = ['Home win', 'Draw', 'Away win'];

export function outcomeIndex(h, a) {
  return h > a ? 0 : h === a ? 1 : 2;
}

export function favourite(p) {
  let best = 0;
  for (let i = 1; i < 3; i++) if (p[i] > p[best]) best = i;
  return best;
}

/** Plain-language reading of a forecast for a casual fan. */
export function verdict(m) {
  const [h, d, a] = m.p;
  const fav = favourite(m.p);
  const home = m.home.short;
  const away = m.away.short;
  if (fav === 1) return `Too close to call: a draw is the single most likely result.`;
  const team = fav === 0 ? home : away;
  const p = fav === 0 ? h : a;
  const gap = Math.abs(h - a);
  const inTen = Math.round(p * 10);
  if (gap < 0.08) return `Almost a coin toss, with ${team} a fraction ahead.`;
  if (p >= 0.7) return `${team} are strong favourites: they win about ${inTen} in 10 matches like this.`;
  if (p >= 0.5) return `${team} are favourites, winning about ${inTen} in 10 matches like this.`;
  return `${team} are slight favourites, but ${fav === 0 ? away : home} or a draw is more likely than not (${pct(1 - p)}).`;
}

export const LEAGUE_ORDER = [
  'premier_league',
  'champions_league',
  'la_liga',
  'bundesliga',
  'serie_a',
  'ligue_1',
];

export const LEAGUE_SHORT = {
  premier_league: 'Premier League',
  champions_league: 'Champions League',
  la_liga: 'LaLiga',
  bundesliga: 'Bundesliga',
  serie_a: 'Serie A',
  ligue_1: 'Ligue 1',
  eredivisie: 'Eredivisie',
  primeira_liga: 'Primeira Liga',
  belgian_pro: 'Belgian Pro League',
  scottish_prem: 'Scottish Premiership',
  super_lig: 'Süper Lig',
  greek_super: 'Greek Super League',
  austrian_bl: 'Austrian Bundesliga',
  swiss_super: 'Swiss Super League',
  danish_super: 'Danish Superliga',
  eliteserien: 'Eliteserien',
};

/** Log loss of one forecast given the outcome index. */
export const logLoss = (p, y) => -Math.log(Math.max(p[y], 1e-12));
