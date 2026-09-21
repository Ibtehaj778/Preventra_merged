import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../data/api';

const PatientsContext = createContext(null);

export function PatientsProvider({ children }) {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  useEffect(() => {
    api.getPatients({ page: 0, page_size: 10000, sort_by: "dropout_prob", sort_dir: "desc" })
      .then((res) => setPatients(res.patients))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <PatientsContext.Provider value={{ patients, loading, error }}>
      {children}
    </PatientsContext.Provider>
  );
}

export const usePatients = () => useContext(PatientsContext);
