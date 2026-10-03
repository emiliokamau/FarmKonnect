// src/components/EventsList.js
import React, { useEffect, useState } from 'react';
import { Table, TableHead, TableRow, TableCell, TableBody, Paper, Alert, CircularProgress, TextField, MenuItem } from '@mui/material';
import api from '../api';

const categoryOptions = [
  { value: 'training', label: 'Training / Workshop' },
  { value: 'grant', label: 'Grant Opportunity' },
];

const EventsList = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [category, setCategory] = useState('');

  const fetchEvents = async (cat = '') => {
    try {
      setError('');
      const params = cat ? { category: cat } : {};
      const resp = await api.get('events/', { params });
      setEvents(resp.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleCategoryChange = (e) => {
    const val = e.target.value;
    setCategory(val);
    setLoading(true);
    fetchEvents(val);
  };

  return (
    <Paper sx={{ p: 3 }}>
      <h2>Training & Grants</h2>
      <TextField
        select
        label="Category"
        value={category}
        onChange={handleCategoryChange}
        sx={{ mb: 2, minWidth: 200 }}
      >
        <MenuItem value="">All</MenuItem>
        {categoryOptions.map((opt) => (
          <MenuItem key={opt.value} value={opt.value}>
            {opt.label}
          </MenuItem>
        ))}
      </TextField>

      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}

      {events.length > 0 && (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Start</TableCell>
              <TableCell>End</TableCell>
              <TableCell>Location</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {events.map((ev) => (
              <TableRow key={ev.id}>
                <TableCell>{ev.title}</TableCell>
                <TableCell>{ev.category}</TableCell>
                <TableCell>{ev.start_date}</TableCell>
                <TableCell>{ev.end_date}</TableCell>
                <TableCell>{ev.location}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Paper>
  );
};

export default EventsList;
