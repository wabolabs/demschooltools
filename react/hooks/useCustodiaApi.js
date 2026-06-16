import { useState, useCallback, useRef } from 'react';

const CSRF_HEADER = {
  'X-CSRFToken': typeof document !== 'undefined'
    ? document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || ''
    : '',
};

async function apiCall(url, options = {}) {
  const fullUrl = url.startsWith('/') ? `/custodia-api${url}` : `/custodia-api/${url}`;
  const res = await fetch(fullUrl, {
    headers: { 'Content-Type': 'application/json', ...CSRF_HEADER, ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const ct = res.headers.get('content-type');
  return ct && ct.includes('application/json') ? res.json() : res.text();
}

export function useCustodiaApi() {
  const [students, setStudents] = useState([]);
  const [studentDetail, setStudentDetail] = useState(null);
  const [reports, setReports] = useState([]);
  const [years, setYears] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const studentCache = useRef({});

  const loadStudents = useCallback(async (force) => {
    if (!force && students.length > 0) return students;
    setLoading(true);
    try {
      const data = await apiCall('/students');
      setStudents(data.students || []);
      setError(null);
      return data.students || [];
    } catch (e) { setError(e.message); return []; }
    finally { setLoading(false); }
  }, [students.length]);

  const loadStudent = useCallback(async (id, force) => {
    if (!force && studentCache.current[id]) {
      setStudentDetail(studentCache.current[id]);
      return studentCache.current[id];
    }
    setLoading(true);
    try {
      const data = await apiCall(`/students/${id}`);
      const s = data.student || data;
      studentCache.current[id] = s;
      setStudentDetail(s);
      setError(null);
      return s;
    } catch (e) { setError(e.message); return null; }
    finally { setLoading(false); }
  }, []);

  const swipeStudent = useCallback(async (student, direction, overrideTime) => {
    let overrideDate;
    if (overrideTime) {
      overrideDate = direction === 'in'
        ? new Date().toISOString().substr(0, 10)
        : student.last_swipe_date;
    }
    const data = await apiCall(`/students/${student._id}/swipe`, {
      method: 'POST',
      body: JSON.stringify({ direction, overrideDate, overrideTime }),
    });
    setStudents(data.students || []);
    return data;
  }, []);

  const markAbsent = useCallback(async (student) => {
    await apiCall(`/students/${student._id}/absent`, { method: 'POST' });
    return loadStudents(true);
  }, [loadStudents]);

  const deleteSwipe = useCallback(async (swipe, student) => {
    const data = await apiCall(`/students/${student._id}/swipe/delete`, {
      method: 'POST',
      body: JSON.stringify({ swipe }),
    });
    const s = data.student || data;
    studentCache.current[student._id] = s;
    setStudentDetail(s);
    return s;
  }, []);

  const excuseStudent = useCallback(async (studentId, day, undo) => {
    const data = await apiCall(`/students/${studentId}/excuse`, {
      method: 'POST',
      body: JSON.stringify({ day, undo }),
    });
    const s = data.student || data;
    studentCache.current[studentId] = s;
    setStudentDetail(s);
    return s;
  }, []);

  const overrideStudent = useCallback(async (studentId, day, undo) => {
    const data = await apiCall(`/students/${studentId}/override`, {
      method: 'POST',
      body: JSON.stringify({ day, undo }),
    });
    const s = data.student || data;
    studentCache.current[studentId] = s;
    setStudentDetail(s);
    return s;
  }, []);

  const updateStudent = useCallback(async (id, start_date, minutes) => {
    const data = await apiCall(`/students/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ start_date, minutes }),
    });
    const s = data.student || data;
    studentCache.current[id] = s;
    setStudentDetail(s);
    return s;
  }, []);

  const loadYears = useCallback(async () => {
    try {
      const data = await apiCall('/reports/years');
      setYears(data);
      return data;
    } catch (e) { return { years: [], current_year: '' }; }
  }, []);

  const loadReport = useCallback(async (yearName, filterStudents) => {
    setLoading(true);
    try {
      const url = filterStudents ? `/reports/${yearName}?filterStudents=${filterStudents}` : `/reports/${yearName}`;
      const data = await apiCall(url);
      setReports(data);
      return data;
    } catch (e) { setError(e.message); return []; }
    finally { setLoading(false); }
  }, []);

  const createPeriod = useCallback(async (name, from, to) => {
    await apiCall('/reports/years', {
      method: 'POST',
      body: JSON.stringify({ name, from, to }),
    });
    return loadYears();
  }, [loadYears]);

  const deletePeriod = useCallback(async (name) => {
    await apiCall(`/reports/years/${encodeURIComponent(name)}`, { method: 'DELETE' });
    return loadYears();
  }, [loadYears]);

  return {
    students, studentDetail, reports, years, loading, error,
    loadStudents, loadStudent, swipeStudent, markAbsent,
    deleteSwipe, excuseStudent, overrideStudent, updateStudent,
    loadYears, loadReport, createPeriod, deletePeriod,
  };
}
