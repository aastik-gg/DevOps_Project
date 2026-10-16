import { CONDITION_LABELS, STATUS_LABELS, daysOverdue, formatDate, formatDue } from '../lib/format.js';

export default function ItemCard({ item, busy, onCheckOut, onReturn, onEdit, onDelete }) {
  const loan = item.active_loan;
  const late = loan ? daysOverdue(loan.due_at) : 0;

  return (
    <article className={`card card-${item.status.toLowerCase()}`}>
      <div className="card-top">
        <span className="tag">{item.asset_tag}</span>
        <span className={`pill pill-${item.status.toLowerCase()}`}>{STATUS_LABELS[item.status]}</span>
      </div>
      <h3 className="card-title">{item.name}</h3>
      <dl className="card-meta">
        <div>
          <dt>Category</dt>
          <dd>{item.category}</dd>
        </div>
        <div>
          <dt>Location</dt>
          <dd>{item.location || '—'}</dd>
        </div>
        <div>
          <dt>Condition</dt>
          <dd className={`cond cond-${item.condition.toLowerCase()}`}>{CONDITION_LABELS[item.condition]}</dd>
        </div>
      </dl>

      {loan && (
        <div className={`loan ${late ? 'loan-late' : ''}`}>
          <div className="loan-who">
            <span className="avatar" aria-hidden="true">
              {loan.borrower.trim().charAt(0).toUpperCase()}
            </span>
            <div>
              <strong>{loan.borrower}</strong>
              {loan.purpose && <span className="muted small"> · {loan.purpose}</span>}
            </div>
          </div>
          <div className="loan-due">
            <span>{formatDue(loan.due_at)}</span>
            <span className="muted small">due {formatDate(loan.due_at)}</span>
          </div>
        </div>
      )}

      {item.notes && !loan && <p className="card-notes">{item.notes}</p>}

      <div className="card-actions">
        {loan ? (
          <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={() => onReturn(item)}>
            Mark returned
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={busy || item.status !== 'AVAILABLE'}
            title={item.status === 'MAINTENANCE' ? 'Needs repair before it can be lent out' : undefined}
            onClick={() => onCheckOut(item)}
          >
            Check out
          </button>
        )}
        <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => onEdit(item)}>
          Edit
        </button>
        <button type="button" className="btn btn-ghost btn-sm btn-danger" disabled={busy} onClick={() => onDelete(item)}>
          Delete
        </button>
      </div>
    </article>
  );
}
