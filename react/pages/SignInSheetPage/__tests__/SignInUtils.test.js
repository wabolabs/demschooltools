import { describe, expect, it } from 'vitest';
import {
  sortPeopleByName,
  getPdfFontSizeForName,
  splitRosterByRole,
  assignDisplayIndices,
  buildTableRows,
  buildGuestStaffRows,
  addBlankRowsToStudents,
  addBlankRowsToGuestStaff,
} from '../SignInUtils';

describe('sortPeopleByName', () => {
  it('sorts by last name', () => {
    const a = { name: 'Charlie Brown' };
    const b = { name: 'Alice Smith' };
    expect(sortPeopleByName(a, b)).toBeGreaterThan(0);
    expect(sortPeopleByName(b, a)).toBeLessThan(0);
  });

  it('sorts by first name when last names match', () => {
    const a = { name: 'Alice Smith' };
    const b = { name: 'Bob Smith' };
    expect(sortPeopleByName(a, b)).toBeLessThan(0);
  });
});

describe('getPdfFontSizeForName', () => {
  it('returns 10 for short names', () => {
    expect(getPdfFontSizeForName('Alice')).toBe(10);
  });

  it('returns 9 for medium names', () => {
    expect(getPdfFontSizeForName('Christopher Anderson')).toBe(9);
  });

  it('returns 8 for long names', () => {
    expect(getPdfFontSizeForName('Christopher Alexander Anderson')).toBe(8);
  });

  it('returns 7 for very long names', () => {
    expect(getPdfFontSizeForName('Christopher Alexander Anderson-Smith')).toBe(7);
  });
});

describe('splitRosterByRole', () => {
  it('splits students, guests, and staff', () => {
    const roster = [
      { name: 'Alice', role: 'student' },
      { name: 'Bob', role: 'guest' },
      { name: 'Carol', role: 'staff' },
    ];
    const result = splitRosterByRole(roster);
    expect(result.students).toHaveLength(1);
    expect(result.guests).toHaveLength(1);
    expect(result.staff).toHaveLength(1);
  });

  it('defaults to student role', () => {
    const roster = [{ name: 'Unspecified' }];
    const result = splitRosterByRole(roster);
    expect(result.students).toHaveLength(1);
  });
});

describe('assignDisplayIndices', () => {
  it('assigns sequential indices', () => {
    const students = [{ name: 'A' }, { name: 'B' }];
    const guests = [{ name: 'C' }];
    const staff = [{ name: 'D' }];
    const result = assignDisplayIndices(students, guests, staff);
    expect(result.students[0].displayIndex).toBe(1);
    expect(result.students[1].displayIndex).toBe(2);
    expect(result.guests[0].displayIndex).toBe(3);
    expect(result.staff[0].displayIndex).toBe(4);
  });
});

describe('buildTableRows', () => {
  it('builds rows in correct order', () => {
    const students = [{ name: 'Student' }];
    const guests = [{ name: 'Guest' }];
    const staff = [{ name: 'Staff' }];
    const rows = buildTableRows(students, guests, staff);
    expect(rows).toHaveLength(4);
    expect(rows[0].name).toBe('Student');
    expect(rows[1].type).toBe('section');
    expect(rows[1].label).toBe('Guests & Volunteers');
    expect(rows[2].name).toBe('Guest');
    expect(rows[3].type).toBe('section');
    expect(rows[3].label).toBe('Staff');
  });
});

describe('buildGuestStaffRows', () => {
  it('returns empty for no guests or staff', () => {
    expect(buildGuestStaffRows([], [])).toEqual([]);
  });

  it('creates section headers', () => {
    const rows = buildGuestStaffRows([{ name: 'G' }], [{ name: 'S' }]);
    expect(rows).toHaveLength(4);
  });
});

describe('addBlankRowsToStudents', () => {
  it('returns empty for empty input', () => {
    expect(addBlankRowsToStudents([])).toEqual([]);
  });

  it('adds blanks to fill up to ROWS_PER_PAGE', () => {
    const students = [{ name: 'A', displayIndex: 1 }];
    const result = addBlankRowsToStudents(students);
    expect(result).toHaveLength(18);
  });

  it('does not add blanks when count is exact multiple', () => {
    const students = Array.from({ length: 18 }, (_, i) => ({
      name: `S${i}`,
      displayIndex: i + 1,
    }));
    const result = addBlankRowsToStudents(students);
    expect(result).toHaveLength(18);
  });
});

describe('addBlankRowsToGuestStaff', () => {
  it('returns empty for no guests or staff', () => {
    expect(addBlankRowsToGuestStaff([], [], 0)).toEqual([]);
  });

  it('numbers guests and staff correctly', () => {
    const guests = [];
    const staff = [{ name: 'Staff1' }];
    const result = addBlankRowsToGuestStaff(guests, staff, 20);
    expect(result[0].displayIndex).toBe(20);
  });
});
