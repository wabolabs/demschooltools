import { describe, expect, it } from 'vitest';
import { normalizeOption, buildOptionMap } from '../minutesUtils';

describe('normalizeOption', () => {
  it('returns the option if it is a string', () => {
    expect(normalizeOption('hello')).toBe('hello');
  });

  it('returns value property if object', () => {
    expect(normalizeOption({ value: 'foo', label: 'Foo' })).toBe('foo');
  });

  it('returns toString() for number', () => {
    expect(normalizeOption(42)).toBe('42');
  });
});

describe('buildOptionMap', () => {
  it('builds a map from option array', () => {
    const options = [
      { value: 'a', label: 'A' },
      { value: 'b', label: 'B' },
    ];
    const map = buildOptionMap(options);
    expect(map.get('a')).toBe('A');
    expect(map.get('b')).toBe('B');
  });
});
