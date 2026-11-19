import { Info } from 'lucide-react';
import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

// Only one explanation open at a time.
const OPEN_EVENT = 'xg-tip-open';

/**
 * A plain-words explanation for a stat, chart or label. Opens on hover (mouse),
 * on keyboard focus, and on tap (phones have no hover). Escape, a tap
 * elsewhere, or scrolling closes it.
 *
 *   <Tip text="…">Expected goals</Tip>   label followed by an (i) button
 *   <Tip text="…" />                      (i) button only
 */
export default function Tip({ text, children, label, className = '' }) {
  const id = useId();
  const btn = useRef(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(null);
  const hoverTimer = useRef(null);

  const show = () => {
    window.dispatchEvent(new CustomEvent(OPEN_EVENT, { detail: id }));
    setOpen(true);
  };
  const hide = () => setOpen(false);

  useEffect(() => {
    const other = (e) => e.detail !== id && setOpen(false);
    window.addEventListener(OPEN_EVENT, other);
    return () => window.removeEventListener(OPEN_EVENT, other);
  }, [id]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && (setOpen(false), btn.current?.focus());
    const onDown = (e) => {
      if (!btn.current?.contains(e.target) && !document.getElementById(`${id}-pop`)?.contains(e.target)) setOpen(false);
    };
    const onScroll = () => setOpen(false);
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onDown);
    window.addEventListener('scroll', onScroll, { passive: true, capture: true });
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onDown);
      window.removeEventListener('scroll', onScroll, { capture: true });
    };
  }, [open, id]);

  // Place above the button, clamped inside the viewport; flip below if there's no room.
  useLayoutEffect(() => {
    if (!open || !btn.current) return;
    const r = btn.current.getBoundingClientRect();
    const width = Math.min(280, window.innerWidth - 24);
    const left = Math.max(12, Math.min(r.left + r.width / 2 - width / 2, window.innerWidth - width - 12));
    const below = r.top < 140;
    setPos({ left, width, top: below ? r.bottom + 8 : r.top - 8, below });
  }, [open]);

  const onEnter = (e) => {
    if (e.pointerType !== 'mouse') return;
    clearTimeout(hoverTimer.current);
    hoverTimer.current = setTimeout(show, 120);
  };
  const onLeave = (e) => {
    if (e.pointerType !== 'mouse') return;
    clearTimeout(hoverTimer.current);
    hoverTimer.current = setTimeout(hide, 160);
  };

  return (
    <span className={`tip ${className}`}>
      {children}
      <button
        ref={btn}
        type="button"
        className="tip__btn"
        aria-label={label ? `What is ${label}?` : 'Explain this'}
        aria-expanded={open}
        aria-describedby={open ? `${id}-pop` : undefined}
        onClick={() => (open ? hide() : show())}
        onFocus={show}
        onBlur={(e) => !document.getElementById(`${id}-pop`)?.contains(e.relatedTarget) && hide()}
        onPointerEnter={onEnter}
        onPointerLeave={onLeave}
      >
        <Info aria-hidden="true" size={14} strokeWidth={2.25} />
      </button>
      {open &&
        pos &&
        createPortal(
          <span
            id={`${id}-pop`}
            role="tooltip"
            className={`tip__pop${pos.below ? ' tip__pop--below' : ''}`}
            style={{ left: pos.left, top: pos.top, width: pos.width }}
            onPointerEnter={(e) => e.pointerType === 'mouse' && clearTimeout(hoverTimer.current)}
            onPointerLeave={onLeave}
          >
            {text}
          </span>,
          document.body,
        )}
    </span>
  );
}
