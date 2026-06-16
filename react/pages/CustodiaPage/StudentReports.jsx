import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Button, Select, MenuItem, FormControl,
  InputLabel, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
} from '@mui/material';
import { useCustodiaApi } from '../../hooks/useCustodiaApi';

export default function StudentReports() {
  const { years, reports, loadYears, loadReport, createPeriod, deletePeriod } = useCustodiaApi();
  const [selectedYear, setSelectedYear] = useState('');
  const [filter, setFilter] = useState('current');
  const [openDialog, setOpenDialog] = useState(false);
  const [newPeriod, setNewPeriod] = useState({ name: '', from: '', to: '' });

  useEffect(() => { loadYears(); }, []);

  useEffect(() => {
    if (years?.current_year) setSelectedYear(years.current_year);
  }, [years]);

  useEffect(() => {
    if (selectedYear) loadReport(selectedYear, filter);
  }, [selectedYear, filter]);

  const handleCreate = async () => {
    await createPeriod(newPeriod.name, newPeriod.from, newPeriod.to);
    setOpenDialog(false);
    setNewPeriod({ name: '', from: '', to: '' });
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Year</InputLabel>
          <Select value={selectedYear} label="Year" onChange={e => setSelectedYear(e.target.value)}>
            {(years?.years || []).map(y => (
              <MenuItem key={y} value={y}>{y}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Filter</InputLabel>
          <Select value={filter} label="Filter" onChange={e => setFilter(e.target.value)}>
            <MenuItem value="current">Current students</MenuItem>
            <MenuItem value="all">All attendees</MenuItem>
          </Select>
        </FormControl>
        <Button variant="outlined" onClick={() => setOpenDialog(true)}>New Period</Button>
      </Box>

      {reports.length > 0 ? (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell align="right">Attended</TableCell>
                <TableCell align="right">Overrides</TableCell>
                <TableCell align="right">Unexcused</TableCell>
                <TableCell align="right">Excused</TableCell>
                <TableCell align="right">Short</TableCell>
                <TableCell align="right">Hours</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reports.map(r => (
                <TableRow key={r._id || r.person_id}>
                  <TableCell>{r.name}</TableCell>
                  <TableCell align="right">{r.good || 0}</TableCell>
                  <TableCell align="right">{r.overrides || 0}</TableCell>
                  <TableCell align="right">{r.unexcused || 0}</TableCell>
                  <TableCell align="right">{r.excuses || 0}</TableCell>
                  <TableCell align="right">{r.short || 0}</TableCell>
                  <TableCell align="right">{r.total_hours?.toFixed(1) || '0'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Typography color="text.secondary">Select a year to view report data.</Typography>
      )}

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>Create new period</DialogTitle>
        <DialogContent>
          <TextField label="Name" fullWidth sx={{ mt: 1 }}
            value={newPeriod.name} onChange={e => setNewPeriod(p => ({ ...p, name: e.target.value }))} />
          <TextField label="From" type="datetime-local" fullWidth sx={{ mt: 1 }}
            value={newPeriod.from} onChange={e => setNewPeriod(p => ({ ...p, from: e.target.value }))} />
          <TextField label="To" type="datetime-local" fullWidth sx={{ mt: 1 }}
            value={newPeriod.to} onChange={e => setNewPeriod(p => ({ ...p, to: e.target.value }))} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
