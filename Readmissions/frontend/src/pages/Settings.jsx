import React from 'react';
import { API_BASE_URL } from '../api';
import { getToken, readClaims } from '../api/auth';
import UserManagement from '../components/shared/UserManagement';

// Accounts are shared by both apps, and so is this page: GLP-1 shows the same
// User Management in its Settings. The auth service is this app's own API.
export default function Settings() {
  const me = readClaims();
  const isManager = me?.role === 'superadmin' || me?.role === 'hospital_admin';

  return (
    <div className="mx-auto max-w-6xl p-4 md:p-6">
      {isManager ? (
        <UserManagement authBaseUrl={API_BASE_URL} getToken={getToken} me={me} />
      ) : (
        <p className="text-sm text-gray-500">
          User Management is for hospital administrators. Ask yours to change your
          role or access.
        </p>
      )}
    </div>
  );
}
