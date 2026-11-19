import { useEffect, useState } from 'react';
import { OUTCOME, pctNum } from '../lib/data.js';
import { luminance } from '../lib/kit.js';

/**
 * The signature: a home / draw / away split drawn as shirt panels in the
 * clubs' own colours. Each club panel carries a collar-trim band and a faint
 * pinstripe in its second colour; light shirts (white, pale yellow, sky blue)
 * get a firm outline so they hold their edge in both themes. On first view the
 * panels open from an even three-way split to the forecast.
 */
export default function KitBar({ p, kits, size = 'row', settle = true, label }) {
  const [open, setOpen] = useState(!settle);
  useEffect(() => {
    if (!settle) return undefined;
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setOpen(true)));
    return () => cancelAnimationFrame(id);
  }, [settle]);

  const parts = [
    { key: 'home', grow: p[0], kit: kits.home },
    { key: 'draw', grow: p[1] },
    { key: 'away', grow: p[2], kit: kits.away },
  ];
  const aria = label ?? OUTCOME.map((o, i) => `${o} ${pctNum(p[i])}%`).join(', ');

  return (
    <div className={`kitbar kitbar--${size}`} role="img" aria-label={aria}>
      {parts.map((s) => {
        const light = s.kit && luminance(s.kit[0]) > 0.6;
        return (
          <span
            key={s.key}
            className={`kitbar__panel kitbar__panel--${s.key}${light ? ' kitbar__panel--light' : ''}`}
            style={{
              flexGrow: open ? Math.max(s.grow, 0.004) : 1,
              ...(s.kit ? { '--main': s.kit[0], '--trim': s.kit[1] } : null),
            }}
          />
        );
      })}
    </div>
  );
}
