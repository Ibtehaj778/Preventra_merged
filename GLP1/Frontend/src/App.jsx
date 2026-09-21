import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { RoleProvider } from './context/RoleContext';
import { PatientsProvider } from './context/PatientsContext';
import AppShell from './components/layout/AppShell';
import LoadingScreen from './components/shared/LoadingScreen';
import ChatWidget from './components/chatbot/ChatWidget';
import { useAppLoader } from './hooks/useAppLoader';
import Login from './pages/Login';
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

function RootRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/*"
        element={isAuthenticated ? <AuthenticatedApp /> : <Navigate to="/login" replace />}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <RootRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}