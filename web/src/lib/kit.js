// Club colours, and the kit-clash rule: when the two sides' colours are too
// close to tell apart, the away side changes into its second colour, the way
// referees make teams change kit on matchday.

const NEUTRAL = ['#7C879E', '#C9CFDA'];

function rgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** "Redmean" perceptual colour distance, 0..~765. */
export function distance(a, b) {
  const [r1, g1, b1] = rgb(a);
  const [r2, g2, b2] = rgb(b);
  const rm = (r1 + r2) / 2;
  const dr = r1 - r2;
  const dg = g1 - g2;
  const db = b1 - b2;
  return Math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db);
}

export function luminance(hex) {
  const c = rgb(hex).map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}

/** Ink that reads on a given background colour. */
export const inkOn = (hex) => (luminance(hex) > 0.4 ? '#0B1733' : '#FFFFFF');

const CLASH = 150;

/**
 * Colours for a fixture: { home: [main, trim], away: [main, trim], changed }.
 * `changed` is true when the away side switched to its second colour.
 */
export function fixtureKits(home, away) {
  const h = home.kit || NEUTRAL;
  let a = away.kit || NEUTRAL;
  let changed = false;
  if (distance(h[0], a[0]) < CLASH) {
    const alt = [a[1], a[0]];
    if (distance(h[0], alt[0]) >= CLASH) {
      a = alt;
      changed = true;
    } else {
      a = NEUTRAL;
      changed = true;
    }
  }
  return { home: h, away: a, changed };
}

/** Blend a colour toward a background (alpha 0..1), returning hex. */
export function mix(hex, bg, alpha) {
  const f = rgb(hex);
  const b = rgb(bg);
  const out = f.map((v, i) => Math.round(v * alpha + b[i] * (1 - alpha)));
  return `#${out.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
}
