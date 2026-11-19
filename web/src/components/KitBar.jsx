import { useEffect, useState } from 'react';
import { OUTCOME, pctNum } from '../lib/data.js';

/**
 * The signature: a home / draw / away split drawn as shirt panels in the
 * clubs' own colours, each panel trimmed with the club's second colour like a
 * collar band. On first view the panels open from an even three-way split to
 * the forecast.
 */
export default function KitBar({ p, kits, size = 'row', settle = true, label }) {
  const [open, setOpen] = useState(!settle);
  useEffect(() => {
    if (!settle) return undefined;
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setOpen(true)));
    return () => cancelAnimationFrame(id);
  }, [settle]);

  const parts = [
    { key: 'home', grow: p[0], main: kits.home[0], trim: kits.home[1] },
    { key: 'draw', grow: p[1] },
    { key: 'away', grow: p[2], main: kits.away[0], trim: kits.away[1] },
  ];
  const aria =
    label ?? OUTCOME.map((o, i) => `${o} ${pctNum(p[i])}%`).join(', ');

  return (
    <div className={`kitbar kitbar--${size}`} role="img" aria-label={aria}>
      {parts.map((s) => (
        <span
          key={s.key}
          className={`kitbar__panel kitbar__panel--${s.key}`}
          style={{
            flexGrow: open ? Math.max(s.grow, 0.004) : 1,
            ...(s.main ? { '--main': s.main, '--trim': s.trim } : null),
          }}
        />
      ))}
    </div>
  );
}
