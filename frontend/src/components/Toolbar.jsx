import { STATUS_LABELS } from '../lib/format.js';

const FILTERS = [['', 'All'], ...Object.entries(STATUS_LABELS)];

export default function Toolbar({ status, onStatus, query, onQuery, counts }) {
  return (
    <div className="toolbar">
      <div className="chips" role="tablist" aria-label="Filter by status">
        {FILTERS.map(([value, label]) => (
          <button
            key={value || 'all'}
            type="button"
            role="tab"
            aria-selected={status === value}
            className={`chip ${status === value ? 'chip-on' : ''} ${value ? `chip-${value.toLowerCase()}` : ''}`}
            onClick={() => onStatus(value)}
          >
            {label}
            {counts && <span className="chip-count">{value ? counts[value] ?? 0 : counts.ALL}</span>}
          </button>
        ))}
      </div>
      <label className="search">
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <circle cx="9" cy="9" r="6" />
          <path d="M14 14l4 4" />
        </svg>
        <input
          type="search"
          placeholder="Search name, tag, category…"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          aria-label="Search equipment"
        />
      </label>
    </div>
  );
}
