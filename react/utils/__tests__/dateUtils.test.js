import { describe, expect, it } from 'vitest';
import { formatDate, formatShortDate, parseDateWithNoTime } from '../dateUtils';

describe('formatDate', () => {
  it('returns empty string for null', () => {
    expect(formatDate(null)).toBe('');
  });

  it('returns empty string for undefined', () => {
    expect(formatDate(undefined)).toBe('');
  });

  it('formats a Date object', () => {
    const d = new Date(2025, 0, 15);
    expect(formatDate(d)).toBe('January 15, 2025');
  });

  it('parses an ISO string', () => {
    expect(formatDate('2025-06-01')).toBe('June 1, 2025');
  });
});

describe('formatShortDate', () => {
  it('returns empty string for null', () => {
    expect(formatShortDate(null)).toBe('');
  });

  it('formats a Date object as short', () => {
    const d = new Date(2025, 5, 15);
    expect(formatShortDate(d)).toBe('Jun 15');
  });
});

describe('parseDateWithNoTime', () => {
  it('returns empty string for null', () => {
    expect(parseDateWithNoTime(null)).toBe('');
  });

  it('parses "2025-06-15" correctly', () => {
    const result = parseDateWithNoTime('2025-06-15');
    expect(result.getFullYear()).toBe(2025);
    expect(result.getMonth()).toBe(5);
    expect(result.getDate()).toBe(15);
  });

  it('returns empty string for invalid format', () => {
    expect(parseDateWithNoTime('not-a-date')).toBe('');
  });
});
