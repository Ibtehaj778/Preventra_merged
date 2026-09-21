import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import PatientDetail from './pages/PatientDetail';
import PatientTrend from './pages/PatientTrend';
import UpdatePatient from './pages/UpdatePatient';
import Analytics from './pages/Analytics';
import DoctorConsole from './pages/DoctorConsole';
import ManualEntry from './pages/ManualEntry';
import About from './pages/About';
import TestComponents from './pages/TestComponents';
import { MANUAL_ENTRY_ENABLED } from './api';

/**
 * The care-team dashboard.
 *
 * There is no sign-in and there are no roles: every visitor gets the full
 * clinical view. The only gate in front of the data is the API key the client
 * sends on each request (see api/index.js), which is a deployment control and
 * not user authentication.
 */
function App() {
  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/patients/:id" element={<PatientDetail />} />
          <Route path="/patients/:id/trend" element={<PatientTrend />} />
          <Route path="/patients/:id/update" element={<UpdatePatient />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/doctor" element={<DoctorConsole />} />
          {/* Off by default. The backend refuses the create endpoints too, so
              typing the URL gets you a form that cannot save. */}
          {MANUAL_ENTRY_ENABLED && <Route path="/manual-entry" element={<ManualEntry />} />}
          <Route path="/about" element={<About />} />
          <Route path="/test-components" element={<TestComponents />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
