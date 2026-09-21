import { createContext, useContext, useState } from 'react';

const RoleContext = createContext(null);

export function RoleProvider({ children }) {
  const [role, setRole] = useState('case_manager'); // 'insurer' | 'case_manager'
  return (
    <RoleContext.Provider value={{ role, setRole, isInsurer: role === 'insurer', isCaseManager: role === 'case_manager' }}>
      {children}
    </RoleContext.Provider>
  );
}

export const useRole = () => useContext(RoleContext);
