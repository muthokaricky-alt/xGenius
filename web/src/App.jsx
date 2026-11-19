import { useEffect, useState } from 'react';
import Header from './components/Header.jsx';
import About from './pages/About.jsx';
import Matches from './pages/Matches.jsx';
import Ratings from './pages/Ratings.jsx';
import Record from './pages/Record.jsx';
import { href, useRoute } from './lib/router.js';

const TITLES = {
  matches: 'Upcoming matches',
  results: 'Recent results',
  match: 'Match forecast',
  ratings: 'Power ratings',
  record: 'Track record',
  about: 'How it works',
};

function initialKit() {
  const set = document.documentElement.dataset.kit;
  if (set === 'home' || set === 'away') return set;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'away' : 'home';
}

export default function App() {
  const route = useRoute();
  const [kit, setKit] = useState(initialKit);

  const chooseKit = (k) => {
    setKit(k);
    document.documentElement.dataset.kit = k;
    try {
      localStorage.setItem('xg-kit', k);
    } catch {
      /* storage unavailable: the choice lasts this visit */
    }
  };

  useEffect(() => {
    document.documentElement.dataset.kit = kit;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', kit === 'away' ? '#050B1D' : '#0B1733');
  }, [kit]);

  useEffect(() => {
    document.title = `${TITLES[route.page] || 'Not found'} · xGenius`;
    if (route.page !== 'match') window.scrollTo(0, 0);
  }, [route.page, route.id]);

  let body;
  switch (route.page) {
    case 'matches':
    case 'results':
    case 'match':
      body = <Matches page={route.page} id={route.id} />;
      break;
    case 'ratings':
      body = <Ratings />;
      break;
    case 'record':
      body = <Record />;
      break;
    case 'about':
      body = <About />;
      break;
    default:
      body = (
        <div className="page">
          <h1>Page not found</h1>
          <p>
            <a href={href('/')}>Go to upcoming matches</a>
          </p>
        </div>
      );
  }

  return (
    <>
      <a
        className="skip"
        href="#main"
        onClick={(e) => {
          e.preventDefault(); // the hash belongs to the router
          document.getElementById('main')?.focus();
        }}
      >
        Skip to content
      </a>
      <Header page={route.page} kit={kit} onKit={chooseKit} />
      <main id="main" tabIndex={-1}>
        {body}
      </main>
      <footer className="foot">
        <p>
          <strong>
            <span className="foot__xg">xG</span>enius
          </strong>{' '}
          · Statistical forecasts, not betting advice. Data: football-data.co.uk and football-data.org.
        </p>
        <p>
          <a href="https://github.com/muthokaricky-alt/xGenius" rel="noopener">Source code</a> ·{' '}
          <a href={href('/about')}>How it works</a>
        </p>
      </footer>
    </>
  );
}
