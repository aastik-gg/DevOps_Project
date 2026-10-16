import { formatDate, timeAgo } from '../lib/format.js';

function eventsFrom(loans) {
  const events = [];
  loans.forEach((loan) => {
    events.push({ id: `out-${loan.id}`, kind: 'out', at: loan.borrowed_at, loan });
    if (loan.returned_at) events.push({ id: `in-${loan.id}`, kind: 'in', at: loan.returned_at, loan });
  });
  return events.sort((a, b) => new Date(b.at) - new Date(a.at)).slice(0, 12);
}

export default function ActivityPanel({ loans, error }) {
  const events = eventsFrom(loans);

  return (
    <aside className="activity" aria-label="Recent activity">
      <h2>Recent activity</h2>
      {error && <p className="muted small">Activity unavailable right now.</p>}
      {!error && events.length === 0 && <p className="muted small">No checkouts yet. Lend something out to see it here.</p>}
      <ol className="timeline">
        {events.map((e) => (
          <li key={e.id} className={`event event-${e.kind} ${e.kind === 'out' && e.loan.overdue ? 'event-late' : ''}`}>
            <span className="event-icon" aria-hidden="true">
              {e.kind === 'out' ? '↗' : '↙'}
            </span>
            <div>
              <p>
                <strong>{e.loan.borrower}</strong> {e.kind === 'out' ? 'borrowed' : 'returned'}{' '}
                <strong>{e.loan.item_name}</strong>
              </p>
              <p className="muted small">
                {timeAgo(e.at)}
                {e.kind === 'out' && !e.loan.returned_at && ` · due ${formatDate(e.loan.due_at)}`}
                {e.kind === 'out' && e.loan.overdue && ' · overdue'}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </aside>
  );
}
