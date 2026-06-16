import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Box, Typography, Button, Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Grid,
} from '@mui/material';
import { useCustodiaApi } from '../../hooks/useCustodiaApi';

export default function StudentDetail() {
  const { studentId } = useParams();
  const { studentDetail, loadStudent, swipeStudent, markAbsent, deleteSwipe, excuseStudent, overrideStudent } = useCustodiaApi();
  const [activeDay, setActiveDay] = useState('');

  useEffect(() => { loadStudent(studentId, true); }, [studentId]);

  const getActiveDay = useCallback((s) => {
    if (activeDay) return activeDay;
    if (s?.days?.[0]) return s.days[0].day;
    return '';
  }, [activeDay]);

  const s = studentDetail;
  if (!s) return <Typography>Loading...</Typography>;

  const ad = getActiveDay(s);
  const dayData = s.days?.find(d => d.day === ad);

  const stats = [
    { label: 'Attended', value: s.total_hours?.toFixed(1) || '0', unit: 'hrs' },
    { label: 'Short', value: s.total_short || '0', unit: 'days' },
    { label: 'Unexcused', value: (s.total_abs || 0) - (s.total_excused || 0), unit: 'days' },
    { label: 'Excused', value: s.total_excused || '0', unit: 'days' },
    { label: 'Override', value: s.total_overrides || '0', unit: 'days' },
    { label: 'Required', value: s.required_minutes || '345', unit: 'min' },
  ];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>{s.name}</Typography>
      <Box sx={{ mb: 2 }}>
        <Button variant="contained" color="primary" size="small" sx={{ mr: 1 }}
          onClick={() => swipeStudent(s, 'in')}>Sign In</Button>
        <Button variant="contained" color="primary" size="small" sx={{ mr: 1 }}
          onClick={() => swipeStudent(s, 'out')}>Sign Out</Button>
        <Button variant="outlined" color="secondary" size="small"
          onClick={() => markAbsent(s)}>Absent Today</Button>
      </Box>

      <Grid container spacing={1} sx={{ mb: 2 }}>
        {stats.map(st => (
          <Grid item xs={4} sm={2} key={st.label}>
            <Paper sx={{ p: 1, textAlign: 'center' }}>
              <Typography variant="h6">{st.value}</Typography>
              <Typography variant="caption">{st.label}</Typography>
              <Typography variant="caption" display="block">{st.unit}</Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {dayData && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2">Active Day: {ad}</Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', my: 1 }}>
            <Chip label={dayData.valid ? 'Valid ✓' : 'Invalid'} color={dayData.valid ? 'success' : 'default'} size="small" />
            {dayData.absent && <Chip label="Absent" color="error" size="small" />}
            {dayData.override && <Chip label="Override" color="warning" size="small" />}
            {dayData.excused && <Chip label="Excused" color="info" size="small" />}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button size="small" variant="outlined"
              onClick={() => excuseStudent(s._id, ad, dayData.excused)}>
              {dayData.excused ? 'Un-excuse' : 'Excuse'}
            </Button>
            <Button size="small" variant="outlined"
              onClick={() => overrideStudent(s._id, ad, dayData.override)}>
              {dayData.override ? 'Remove override' : 'Override'}
            </Button>
          </Box>
        </Box>
      )}

      {dayData?.swipes?.length > 0 && (
        <TableContainer component={Paper} sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>In</TableCell>
                <TableCell>Out</TableCell>
                <TableCell></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {dayData.swipes.map(sw => (
                <TableRow key={sw._id}>
                  <TableCell>{sw.in_time && !sw.out_time ? 'In' : 'Out'}</TableCell>
                  <TableCell>{sw.nice_in_time || sw.in_time}</TableCell>
                  <TableCell>{sw.nice_out_time || sw.out_time}</TableCell>
                  <TableCell>
                    <Button size="small" color="error"
                      onClick={() => deleteSwipe(sw, s)}>Delete</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {s.days?.length > 0 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Day</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Minutes</TableCell>
                <TableCell></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {s.days.map(d => (
                <TableRow key={d.day}
                  selected={d.day === ad}
                  hover
                  onClick={() => setActiveDay(d.day)}
                  sx={{ cursor: 'pointer' }}>
                  <TableCell>{d.day}</TableCell>
                  <TableCell>
                    {d.absent ? 'Absent' : d.valid ? 'Attended' : d.override ? 'Override' : d.excused ? 'Excused' : '—'}
                  </TableCell>
                  <TableCell>{d.total_mins}</TableCell>
                  <TableCell>
                    {d.short > 0 && <Chip label={`Short ${d.short}`} size="small" color="warning" />}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Box sx={{ mt: 2 }}>
        <Link to="/custodia">Back to dashboard</Link>
      </Box>
    </Box>
  );
}
