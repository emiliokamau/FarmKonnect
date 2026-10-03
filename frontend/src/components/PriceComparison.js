// src/components/PriceComparison.js
import React, { useState, useEffect } from 'react';
import { TextField, Button, Table, TableHead, TableRow, TableCell, TableBody, Paper, Alert } from '@mui/material';
import api from '../api';

const PriceComparison = () => {
  const [commodity, setCommodity] = useState('MAIZE');
  const [county, setCounty] = useState('Nairobi');
  const [days, setDays] = useState(30);
  const [data, setData] = useState([]);
  const [error, setError] = useState('');

  const fetchTrend = async () => {
    try {
      setError('');
      const resp = await api.get('prices/trend/', {
        params: { commodity, county, days },
      });
      setData(resp.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load data');
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <h2>Market Price Comparison</h2>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        <TextField label="Commodity" value={commodity} onChange={e => setCommodity(e.target.value.toUpperCase())} />
        <TextField label="County" value={county} onChange={e => setCounty(e.target.value)} />
        <TextField label="Days" type="number" value={days} onChange={e => setDays(e.target.value)} />
        <Button variant="contained" onClick={fetchTrend}>Load</Button>
      </div>
      {error && <Alert severity="error">{error}</Alert>}
      {data.length > 0 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Wholesale (KES/kg)</TableCell>
              <TableCell>Retail (KES/kg)</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((row) => (
              <TableRow key={row.date}>
                <TableCell>{row.date}</TableCell>
                <TableCell>{row.wholesale}</TableCell>
                <TableCell>{row.retail}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Paper>
  );
};

export default PriceComparison;
