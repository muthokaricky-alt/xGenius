import { Shirt } from 'lucide-react';
import { href } from '../lib/router.js';

const TABS = [
  { page: 'matches', path: '/', label: 'Matches', also: ['results', 'match'] },
  { page: 'ratings', path: '/ratings', label: 'Ratings' },
  { page: 'record', path: '/record', label: 'Track record' },
  { page: 'about', path: '/about', label: 'How it works' },
];

export function Wordmark() {
  return (
    <a className="wordmark" href={href('/')} aria-label="xGenius home">
      <span className="wordmark__xg">xG</span>enius
    </a>
  );
}

export default function Header({ page, kit, onKit }) {
  const nextKit = kit === 'away' ? 'home' : 'away';
  return (
    <header className="collar">
      <div className="collar__inner">
        <Wordmark />
        <nav className="tabs" aria-label="Main">
          {TABS.map((t) => {
            const active = t.page === page || t.also?.includes(page);
            return (
              <a key={t.page} href={href(t.path)} className="tabs__tab" aria-current={active ? 'page' : undefined}>
                {t.label}
              </a>
            );
          })}
        </nav>
        <button
          type="button"
          className="kit-toggle"
          onClick={() => onKit(nextKit)}
          aria-label={`Switch to ${nextKit === 'away' ? 'dark' : 'light'} theme (${nextKit} kit)`}
          title={`Switch to the ${nextKit} kit`}
        >
          <Shirt aria-hidden="true" size={18} />
          <span>{kit === 'away' ? 'Away kit' : 'Home kit'}</span>
        </button>
      </div>
      <div className="collar__trim" aria-hidden="true" />
    </header>
  );
}
