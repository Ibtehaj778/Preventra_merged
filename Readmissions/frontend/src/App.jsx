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
import Settings from './pages/Settings';
import TestComponents from './pages/TestComponents';
import MyRecord from './pages/MyRecord';
import { MANUAL_ENTRY_ENABLED } from './api';
import { readClaims } from './api/auth';

/**
 * The care-team dashboard.
 *
 * Every visitor is a signed-in account, and the backend shows each one only
 * its own patients (api/access.py): the hospital for its admin and case
 * managers, their assigned patients for doctors and nurses, members for an
 * insurer. A patient gets a single page - their own record. The routes below
 * only decide which pages open; the backend decides what data they get.
 */
function App() {
  if (readClaims()?.role === 'patient') {
    return (
      <Router>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/my-record" element={<MyRecord />} />
            <Route path="/patients/:id" element={<PatientDetail />} />
            <Route path="/patients/:id/trend" element={<PatientTrend />} />
            <Route path="*" element={<Navigate to="/my-record" replace />} />
          </Route>
        </Routes>
      </Router>
    );
  }

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
          <Route path="/settings" element={<Settings />} />
          <Route path="/test-components" element={<TestComponents />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
