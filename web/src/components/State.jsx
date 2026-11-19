import { AlertTriangle, RotateCcw } from 'lucide-react';

export function Loading({ rows = 4, label = 'Loading forecasts' }) {
  return (
    <div className="skeleton" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton__row" />
      ))}
    </div>
  );
}

export function ErrorState({ error, retry, what = 'the forecasts' }) {
  return (
    <div className="notice notice--error" role="alert">
      <AlertTriangle aria-hidden="true" size={20} />
      <div>
        <p className="notice__title">Couldn’t load {what}.</p>
        <p className="notice__body">
          {error?.message || 'The data file did not arrive.'} Check your connection and try again.
        </p>
      </div>
      {retry && (
        <button type="button" className="btn" onClick={retry}>
          <RotateCcw aria-hidden="true" size={16} /> Try again
        </button>
      )}
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="notice">
      <div>
        <p className="notice__title">{title}</p>
        {children && <p className="notice__body">{children}</p>}
      </div>
    </div>
  );
}
