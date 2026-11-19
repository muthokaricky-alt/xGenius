import { useEffect, useState } from 'react';

// Hash routes keep the site a set of static files: no server rewrites needed.
//   #/                 matches
//   #/results          recent results
//   #/match/<id>       one match
//   #/ratings  #/record  #/about

function parse() {
  const path = window.location.hash.replace(/^#/, '') || '/';
  const parts = path.split('/').filter(Boolean);
  return { path, page: parts[0] || 'matches', id: parts[1] || null };
}

export function useRoute() {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    const on = () => setRoute(parse());
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  return route;
}

export const href = (path) => `#${path}`;
