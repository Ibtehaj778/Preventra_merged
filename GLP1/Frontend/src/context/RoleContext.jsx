import { createContext, useContext } from 'react';
import { useAuth } from './AuthContext';

const RoleContext = createContext(null);

// Display names for the fixed roles in Readmissions/api/auth.py:ROLES.
const ROLE_LABELS = {
  superadmin:     'Superadmin',
  hospital_admin: 'Hospital admin',
  doctor:         'Doctor',
  nurse:          'Nurse',
  case_manager:   'Case manager',
  insurer:        'Insurer',
  patient:        'Patient',
};

// Roles whose main view is cost and ROI rather than individual patients.
const COST_VIEW_ROLES = ['superadmin', 'hospital_admin', 'insurer'];

// The role is the one an administrator assigned to the account - read from the
// signed-in user, never chosen here. Hiding a panel is a courtesy; the backend
// decides what each role can actually fetch.
export function RoleProvider({ children }) {
  const { user } = useAuth();
  const role = user?.role || 'case_manager';
  return (
    <RoleContext.Provider value={{
      role,
      roleLabel:  ROLE_LABELS[role] || role,
      isCostView: COST_VIEW_ROLES.includes(role),
    }}>
      {children}
    </RoleContext.Provider>
  );
}

export const useRole = () => useContext(RoleContext);
