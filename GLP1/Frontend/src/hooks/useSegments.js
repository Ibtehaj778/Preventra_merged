import { useState, useEffect } from "react";
import { api } from "../data/api";
import { segmentProfiles as mockSegments } from "../data/mockData";

export function useSegments() {
  const [segments, setSegments] = useState(mockSegments);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  useEffect(() => {
    api.getSegments()
      .then((res) => setSegments(res.segments))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  return { segments, loading, error };
}
