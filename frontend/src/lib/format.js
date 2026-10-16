const DAY_MS = 24 * 60 * 60 * 1000;

// API timestamps are UTC. Postgres sends an offset, SQLite (tests/dev) may not;
// without one the browser would parse them as local time.
const HAS_ZONE = /(Z|[+-]\d{2}:?\d{2})$/i;

export function toDate(value) {
  if (value instanceof Date) return value;
  if (typeof value === 'string' && value.includes('T') && !HAS_ZONE.test(value)) return new Date(`${value}Z`);
  return new Date(value);
}

/** Whole days a loan is past due (0 when not overdue). */
export function daysOverdue(dueAt, now = new Date()) {
  const diff = toDate(now) - toDate(dueAt);
  return diff > 0 ? Math.ceil(diff / DAY_MS) : 0;
}

/** Human label for a due date: "Due today", "Due in 3 days", "Overdue by 2 days". */
export function formatDue(dueAt, now = new Date()) {
  const late = daysOverdue(dueAt, now);
  if (late > 0) return `Overdue by ${late} day${late === 1 ? '' : 's'}`;
  const left = Math.floor((toDate(dueAt) - toDate(now)) / DAY_MS);
  if (left <= 0) return 'Due today';
  if (left === 1) return 'Due tomorrow';
  return `Due in ${left} days`;
}

/** Short relative time for the activity feed: "just now", "5m ago", "3h ago", "2d ago". */
export function timeAgo(value, now = new Date()) {
  const secs = Math.max(0, Math.round((toDate(now) - toDate(value)) / 1000));
  if (secs < 60) return 'just now';
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function formatDate(value) {
  return toDate(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

export const STATUS_LABELS = {
  AVAILABLE: 'Available',
  ON_LOAN: 'On loan',
  OVERDUE: 'Overdue',
  MAINTENANCE: 'Maintenance',
};

export const CONDITION_LABELS = {
  GOOD: 'Good',
  FAIR: 'Fair',
  NEEDS_REPAIR: 'Needs repair',
};
