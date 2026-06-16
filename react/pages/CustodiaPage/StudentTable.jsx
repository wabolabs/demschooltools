import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Paper, Typography, Button, Grid, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField,
} from '@mui/material';
import { useCustodiaApi } from '../../hooks/useCustodiaApi';
import { useSwipeLogic } from '../../hooks/useSwipeLogic';

export default function StudentTable() {
  const navigate = useNavigate();
  const { students, loadStudents, swipeStudent } = useCustodiaApi();
  const [localStudents, setLocalStudents] = useState([]);
  const [swipeDialog, setSwipeDialog] = useState({ open: false, student: null, direction: '' });

  useEffect(() => { loadStudents(true); }, []);

  useEffect(() => {
    setLocalStudents([...students].sort((a, b) => a.name?.toLowerCase() > b.name?.toLowerCase() ? 1 : -1));
  }, [students]);

  const handleSwipe = useCallback(async (student, direction) => {
    if (direction === 'in' && student.last_swipe_type === 'in' && student.in_today) {
      setSwipeDialog({ open: true, student, direction: 'out' });
    } else if (direction === 'out' && student.last_swipe_type === 'out' && student.in_today) {
      setSwipeDialog({ open: true, student, direction: 'in' });
    } else {
      await swipeStudent(student, direction);
    }
  }, [swipeStudent]);

  const handleSwipeWithTime = useCallback(async (overrideTime) => {
    await swipeStudent(swipeDialog.student, swipeDialog.direction, overrideTime);
    setSwipeDialog({ open: false, student: null, direction: '' });
  }, [swipeStudent, swipeDialog]);

  const columns = [
    { label: 'Absent', key: 'absent', students: [], color: '#f8d7da' },
    { label: 'Not Yet In', key: 'notYetIn', students: [], color: '#fff3cd' },
    { label: 'In', key: 'in', students: [], color: '#d4edda' },
    { label: 'Out', key: 'out', students: [], color: '#d1ecf1' },
  ];

  localStudents.forEach(s => {
    if (!s.in_today && s.absent_today) columns[0].students.push(s);
    else if (!s.in_today && !s.absent_today) columns[1].students.push(s);
    else if (s.in_today && s.last_swipe_type === 'in') columns[2].students.push(s);
    else if (s.in_today && s.last_swipe_type === 'out') columns[3].students.push(s);
  });

  return (
    <Box>
      <Grid container spacing={1}>
        {columns.map(col => (
          <Grid item xs={12} sm={6} md={3} key={col.key}>
            <Paper sx={{ bgcolor: col.color, p: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                {col.label} ({col.students.length})
              </Typography>
              {col.students.map(s => (
                <Box key={s._id} sx={{ display: 'flex', gap: 0.5, mb: 0.5 }}>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => navigate(`/custodia/students/${s._id}`)}
                    sx={{ minWidth: 32, px: 0.5, fontSize: 14 }}
                  >
                    📅
                  </Button>
                  <Button
                    size="small"
                    variant="contained"
                    color={s.swiped_today_late ? 'warning' : 'primary'}
                    onClick={() => handleSwipe(s, col.key === 'in' || col.key === 'notYetIn' ? 'in' : 'out')}
                    sx={{ flex: 1, textTransform: 'none', fontSize: 13 }}
                  >
                    {s.name}
                  </Button>
                </Box>
              ))}
            </Paper>
          </Grid>
        ))}
      </Grid>

      <Dialog open={swipeDialog.open} onClose={() => setSwipeDialog({ open: false, student: null, direction: '' })}>
        <DialogTitle>Enter previous {swipeDialog.direction} time for {swipeDialog.student?.name}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Time (HH:MM)"
            type="time"
            fullWidth
            onChange={e => setSwipeDialog(prev => ({ ...prev, time: e.target.value }))}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSwipeDialog({ open: false, student: null, direction: '' })}>Cancel</Button>
          <Button onClick={() => handleSwipeWithTime(swipeDialog.time)} variant="contained">Confirm</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
