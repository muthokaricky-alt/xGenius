import { luminance } from '../lib/kit.js';

/**
 * A club shirt drawn in its own colours: body in the main colour, collar and
 * cuffs in the trim. Light shirts get a darker outline so they hold their
 * shape on a white page (and on the dark theme).
 */
export default function Shirt({ kit, size = 18, className = '' }) {
  const main = kit?.[0] ?? 'var(--draw)';
  const trim = kit?.[1] ?? 'var(--rule-strong)';
  const light = kit ? luminance(kit[0]) > 0.6 : false;
  return (
    <svg
      className={`shirt${light ? ' shirt--light' : ''} ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        className="shirt__body"
        d="M8.2 2.6 3.4 4.9 1.3 9.6l3.6 1.6 1.2-1.4V21.4h11.8V9.8l1.2 1.4 3.6-1.6-2.1-4.7-4.8-2.3c-.7 1.5-2.1 2.4-3.8 2.4S8.9 4.1 8.2 2.6Z"
        fill={main}
      />
      <path d="M8.2 2.6c.7 1.5 2.1 2.4 3.8 2.4s3.1-.9 3.8-2.4" fill="none" stroke={trim} strokeWidth="1.7" />
      <path d="m1.9 8.3 3.4 1.5M22.1 8.3l-3.4 1.5" fill="none" stroke={trim} strokeWidth="1.4" />
    </svg>
  );
}
