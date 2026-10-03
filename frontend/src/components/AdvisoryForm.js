// src/components/AdvisoryForm.js
import React, { useState } from 'react';
import { TextField, Button, MenuItem, Paper, Alert, CircularProgress, Typography } from '@mui/material';
import api from '../api';

const storageOptions = [
  { value: 'immediate', label: 'Sell Immediately' },
  { value: 'store', label: 'Store for Later' },
];

const AdvisoryForm = () => {
  const [commodity, setCommodity] = useState('MAIZE');
  const [quantity, setQuantity] = useState('');
  const [harvestDate, setHarvestDate] = useState('');
  const [storageOption, setStorageOption] = useState('immediate');
  const [advisoryId, setAdvisoryId] = useState(null);
  const [recommendation, setRecommendation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const payload = {
        commodity,
        quantity,
        harvest_date: harvestDate,
        storage_option: storageOption,
      };
      const resp = await api.post('advisories/', payload);
      setAdvisoryId(resp.data.id);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create advisory request');
    } finally {
      setLoading(false);
    }
  };

  const runAdvisory = async () => {
    if (!advisoryId) return;
    setLoading(true);
    setError('');
    try {
      await api.post(`advisories/${advisoryId}/run/`);
      const resp = await api.get(`advisories/${advisoryId}/`);
      setRecommendation(resp.data.recommendation);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to run advisory');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <h2>Post‑Harvest Advisory</h2>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <form onSubmit={handleSubmit}>
        <TextField
          label="Commodity"
          value={commodity}
          onChange={e => setCommodity(e.target.value.toUpperCase())}
          sx={{ mb: 2, mr: 2 }}
        />
        <TextField
          label="Quantity (kg)"
          type="number"
          value={quantity}
          onChange={e => setQuantity(e.target.value)}
          sx={{ mb: 2, mr: 2 }}
          required
        />
        <TextField
          label="Harvest Date"
          type="date"
          value={harvestDate}
          onChange={e => setHarvestDate(e.target.value)}
          sx={{ mb: 2, mr: 2 }}
          InputLabelProps={{ shrink: true }}
          required
        />
        <TextField
          select
          label="Storage Option"
          value={storageOption}
          onChange={e => setStorageOption(e.target.value)}
          sx={{ mb: 2, mr: 2 }}
        >
          {storageOptions.map(opt => (
            <MenuItem key={opt.value} value={opt.value}>
              {opt.label}
            </MenuItem>
          ))}
        </TextField>
        <Button type="submit" variant="contained" disabled={loading} sx={{ mb: 2 }}>
          Submit Request
        </Button>
      </form>

      {advisoryId && (
        <>
          <Button variant="outlined" onClick={runAdvisory} disabled={loading} sx={{ mt: 2 }}>
            Run AI Advisory
          </Button>
        </>
      )}

      {loading && <CircularProgress sx={{ mt: 2 }} />}

      {recommendation && (
        <Typography variant="body1" sx={{ mt: 2 }}>
          <strong>Recommendation:</strong> {recommendation}
        </Typography>
      )}
    </Paper>
  );
};

export default AdvisoryForm;
