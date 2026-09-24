import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { AuthProvider, useAuth, PORTAL_URL } from './context/AuthContext';
import { RoleProvider } from './context/RoleContext';
import { PatientsProvider } from './context/PatientsContext';
import AppShell from './components/layout/AppShell';
import LoadingScreen from './components/shared/LoadingScreen';
import ChatWidget from './components/chatbot/ChatWidget';
import { useAppLoader } from './hooks/useAppLoader';
import ExecutiveSummary from './pages/ExecutiveSummary';
import PatientRiskPanel from './pages/PatientRiskPanel';
import PatientDetail from './pages/PatientDetail';
import SegmentExplorer from './pages/SegmentExplorer';
import SurvivalAnalysis from './pages/SurvivalAnalysis';
import CostEffectiveness from './pages/CostEffectiveness';
import BudgetSimulator from './pages/BudgetSimulator';
import CostOfInaction from './pages/CostOfInaction';
import Settings from './pages/Settings';

function AuthenticatedApp() {
  const { ready, progress, status } = useAppLoader();

  if (!ready) {
    return <LoadingScreen progress={progress} status={status} />;
  }

  return (
    <RoleProvider>
      <PatientsProvider>
        <AppShell>
          <Routes>
            <Route path="/"             element={<ExecutiveSummary />} />
            <Route path="/patients"     element={<PatientRiskPanel />} />
            <Route path="/patients/:id" element={<PatientDetail />} />
            <Route path="/segments"     element={<SegmentExplorer />} />
            <Route path="/survival"     element={<SurvivalAnalysis />} />
            <Route path="/cost"         element={<CostEffectiveness />} />
            <Route path="/budget"       element={<BudgetSimulator />} />
            <Route path="/consequence"  element={<CostOfInaction />} />
            <Route path="/settings"     element={<Settings />} />
            <Route path="*"             element={<Navigate to="/" replace />} />
          </Routes>
          <ChatWidget />
        </AppShell>
      </PatientsProvider>
    </RoleProvider>
  );
}

// GLP-1 no longer has its own login screen — an unauthenticated visitor
// gets sent straight back to the shared Portal instead.
function RedirectToPortal() {
  useEffect(() => {
    window.location.href = PORTAL_URL;
  }, []);
  return <LoadingScreen progress={0} status="Redirecting to sign in..." />;
}

function RootRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/*"
        element={isAuthenticated ? <AuthenticatedApp /> : <RedirectToPortal />}
      />
    </Routes>
  );
}

// The browser can restore an old, frozen page snapshot on Back/Forward
// (bfcache) WITHOUT re-running any of our normal auth-check logic. This
// forces a real, fresh reload whenever that specific situation happens,
// so a stale "still logged in" snapshot can never be shown after logout.
function useBfcacheGuard() {
  useEffect(() => {
    function handlePageShow(event) {
      if (event.persisted) {
        window.location.reload();
      }
    }
    window.addEventListener('pageshow', handlePageShow);
    return () => window.removeEventListener('pageshow', handlePageShow);
  }, []);
}

export default function App() {
  useBfcacheGuard();
  return (
    <AuthProvider>
      <BrowserRouter>
        <RootRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}