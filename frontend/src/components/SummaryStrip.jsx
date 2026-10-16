const SEGMENTS = [
  { key: 'available', status: 'AVAILABLE', label: 'Available' },
  { key: 'on_loan', status: 'ON_LOAN', label: 'On loan' },
  { key: 'overdue', status: 'OVERDUE', label: 'Overdue' },
  { key: 'maintenance', status: 'MAINTENANCE', label: 'Maintenance' },
];

export default function SummaryStrip({ stats }) {
  const total = stats?.total_items ?? 0;
  const util = stats?.utilisation_pct ?? 0;

  return (
    <section className="summary" aria-label="Inventory summary">
      <div className="summary-counts">
        {SEGMENTS.map((s) => (
          <div key={s.key} className={`count count-${s.status.toLowerCase()}`}>
            <span className="count-dot" aria-hidden="true" />
            <span className="count-value">{stats ? stats[s.key] : '–'}</span>
            <span className="count-label">{s.label}</span>
          </div>
        ))}
      </div>
      <div className="summary-util">
        <div className="util-head">
          <span>Utilisation</span>
          <strong>{stats ? `${util}%` : '–'}</strong>
        </div>
        <div className="util-bar" role="img" aria-label={`${util}% of ${total} items are out`}>
          {total > 0 &&
            SEGMENTS.map((s) => (
              <span
                key={s.key}
                className={`util-seg seg-${s.status.toLowerCase()}`}
                style={{ width: `${(100 * stats[s.key]) / total}%` }}
              />
            ))}
        </div>
        <p className="muted small">
          {total} item{total === 1 ? '' : 's'} tracked · {stats?.loans_last_7_days ?? 0} checkouts this week
        </p>
      </div>
    </section>
  );
}
