import { useEffect, useRef, useState } from 'react';

/**
 * A horizontally scrollable row (filter chips) that fades only the edge that
 * has more content beyond it, so a clipped chip reads as "scroll for more"
 * rather than as a broken layout.
 */
export default function ScrollRow({ children, label, className = '' }) {
  const ref = useRef(null);
  const [edges, setEdges] = useState({ start: false, end: false });

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const update = () =>
      setEdges({
        start: el.scrollLeft > 2,
        end: el.scrollLeft + el.clientWidth < el.scrollWidth - 2,
      });
    update();
    el.addEventListener('scroll', update, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => {
      el.removeEventListener('scroll', update);
      ro.disconnect();
    };
  }, []);

  return (
    <div
      ref={ref}
      role="group"
      aria-label={label}
      className={`scrollrow${edges.start ? ' scrollrow--fade-start' : ''}${edges.end ? ' scrollrow--fade-end' : ''} ${className}`}
    >
      {children}
    </div>
  );
}
