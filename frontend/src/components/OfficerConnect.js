// src/components/OfficerConnect.js
import React, { useEffect, useState } from 'react';
import { Table, TableHead, TableRow, TableCell, TableBody, Paper, Alert, CircularProgress } from '@mui/material';
import api from '../api';

const OfficerConnect = () => {
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchOfficers = async () => {
      try {
        const resp = await api.get('users/', { params: { role: 'officer' } });
        setOfficers(resp.data);
      } catch (e) {
        setError(e.response?.data?.detail || 'Failed to load officers');
      } finally {
        setLoading(false);
      }
    };
    fetchOfficers();
  }, []);

  return (
    <Paper sx={{ p: 3 }}>
      <h2>Extension Officers</h2>
      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      {officers.length > 0 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>County</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {officers.map((officer) => (
              <TableRow key={officer.id}>
                <TableCell>{officer.first_name} {officer.last_name}</TableCell>
                <TableCell>{officer.email}</TableCell>
                <TableCell>{officer.county || 'N/A'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Paper>
  );
};

export default OfficerConnect;
