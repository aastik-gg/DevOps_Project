import { describe, expect, it } from 'vitest';
import { daysOverdue, formatDue, timeAgo, toDate } from './format.js';

const now = new Date('2026-10-16T12:00:00Z');

describe('daysOverdue', () => {
  it('is zero before the due date', () => {
    expect(daysOverdue('2026-10-20T12:00:00Z', now)).toBe(0);
  });

  it('rounds partial days up once past due', () => {
    expect(daysOverdue('2026-10-16T06:00:00Z', now)).toBe(1);
    expect(daysOverdue('2026-10-13T12:00:00Z', now)).toBe(3);
  });
});

describe('formatDue', () => {
  it('describes upcoming and late loans', () => {
    expect(formatDue('2026-10-16T20:00:00Z', now)).toBe('Due today');
    expect(formatDue('2026-10-17T13:00:00Z', now)).toBe('Due tomorrow');
    expect(formatDue('2026-10-21T13:00:00Z', now)).toBe('Due in 5 days');
    expect(formatDue('2026-10-15T11:00:00Z', now)).toBe('Overdue by 2 days');
    expect(formatDue('2026-10-16T11:00:00Z', now)).toBe('Overdue by 1 day');
  });
});

describe('timeAgo', () => {
  it('buckets elapsed time', () => {
    expect(timeAgo('2026-10-16T11:59:30Z', now)).toBe('just now');
    expect(timeAgo('2026-10-16T11:45:00Z', now)).toBe('15m ago');
    expect(timeAgo('2026-10-16T09:00:00Z', now)).toBe('3h ago');
    expect(timeAgo('2026-10-14T12:00:00Z', now)).toBe('2d ago');
  });
});

describe('toDate', () => {
  it('treats offset-less API timestamps as UTC', () => {
    expect(toDate('2026-10-16T12:00:00').toISOString()).toBe('2026-10-16T12:00:00.000Z');
    expect(toDate('2026-10-16T12:00:00.123456').toISOString()).toBe('2026-10-16T12:00:00.123Z');
    expect(toDate('2026-10-16T17:30:00+05:30').toISOString()).toBe('2026-10-16T12:00:00.000Z');
    expect(toDate('2026-10-16T12:00:00Z').toISOString()).toBe('2026-10-16T12:00:00.000Z');
  });
});
