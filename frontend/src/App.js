// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Button, Container } from '@mui/material';
import PriceComparison from './components/PriceComparison';
import OfficerConnect from './components/OfficerConnect';
import EventsList from './components/EventsList';
import AdvisoryForm from './components/AdvisoryForm';

function App() {
  return (
    <Router>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            FarmKonnect
          </Typography>
          <Button color="inherit" component={Link} to="/prices">Market Prices</Button>
          <Button color="inherit" component={Link} to="/officers">Officers</Button>
          <Button color="inherit" component={Link} to="/events">Events & Grants</Button>
          <Button color="inherit" component={Link} to="/advisory">Advisory</Button>
        </Toolbar>
      </AppBar>
      <Container sx={{ mt: 4 }}>
        <Routes>
          <Route path="/prices" element={<PriceComparison />} />
          <Route path="/officers" element={<OfficerConnect />} />
          <Route path="/events" element={<EventsList />} />
          <Route path="/advisory" element={<AdvisoryForm />} />
          <Route path="/" element={<Typography>Welcome to FarmKonnect portal.</Typography>} />
        </Routes>
      </Container>
    </Router>
  );
}

export default App;
