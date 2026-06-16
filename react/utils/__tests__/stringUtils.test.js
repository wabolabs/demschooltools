import { describe, expect, it } from 'vitest';
import { nth, oxfordComma } from '../stringUtils';

describe('nth', () => {
  it('returns "1st" for 1', () => {
    expect(nth(1)).toBe('1st');
  });

  it('returns "2nd" for 2', () => {
    expect(nth(2)).toBe('2nd');
  });

  it('returns "3rd" for 3', () => {
    expect(nth(3)).toBe('3rd');
  });

  it('returns "4th" for 4', () => {
    expect(nth(4)).toBe('4th');
  });

  it('returns "11th" for 11', () => {
    expect(nth(11)).toBe('11th');
  });

  it('returns "12th" for 12', () => {
    expect(nth(12)).toBe('12th');
  });

  it('returns "13th" for 13', () => {
    expect(nth(13)).toBe('13th');
  });

  it('returns "21st" for 21', () => {
    expect(nth(21)).toBe('21st');
  });

  it('returns "22nd" for 22', () => {
    expect(nth(22)).toBe('22nd');
  });

  it('returns "23rd" for 23', () => {
    expect(nth(23)).toBe('23rd');
  });
});

describe('oxfordComma', () => {
  it('returns ifempty for empty array', () => {
    expect(oxfordComma([], 'and', 'nothing')).toBe('nothing');
  });

  it('returns single element as-is', () => {
    expect(oxfordComma(['Alice'], 'and', '')).toBe('Alice');
  });

  it('joins two elements with conjunction', () => {
    expect(oxfordComma(['Alice', 'Bob'], 'and', '')).toBe('Alice and Bob');
  });

  it('uses oxford comma for three elements', () => {
    expect(oxfordComma(['Alice', 'Bob', 'Charlie'], 'and', '')).toBe(
      'Alice, Bob, and Charlie'
    );
  });

  it('uses "or" conjunction', () => {
    expect(oxfordComma(['A', 'B', 'C'], 'or', '')).toBe('A, B, or C');
  });
});
