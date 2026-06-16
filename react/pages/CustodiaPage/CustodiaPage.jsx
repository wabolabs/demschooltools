import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, Tabs, Tab, Typography } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import StudentTable from './StudentTable';
import StudentDetail from './StudentDetail';
import StudentReports from './StudentReports';

function CustodiaNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const tab = location.pathname.includes('/reports') ? 1 : 0;

  return (
    <Tabs value={tab} onChange={(_, v) => navigate(v === 0 ? '/custodia' : '/custodia/reports')} sx={{ mb: 2 }}>
      <Tab label="Students" />
      <Tab label="Reports" />
    </Tabs>
  );
}

export default function CustodiaPage() {
  return (
    <Box>
      <CustodiaNav />
      <Routes>
        <Route index element={<Navigate to="students" replace />} />
        <Route path="students" element={<StudentTable />} />
        <Route path="students/:studentId" element={<StudentDetail />} />
        <Route path="reports" element={<StudentReports />} />
      </Routes>
    </Box>
  );
}
