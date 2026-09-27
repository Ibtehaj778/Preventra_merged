import { useState, useEffect } from "react";
import { api } from "../data/api";

// null until loaded - never stand-in segment profiles.
export function useSegments() {
  const [segments, setSegments] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  useEffect(() => {
    let live = true;
    api.getSegments()
      .then((res) => { if (live) setSegments(res.segments); })
      .catch((err) => { if (live) setError(err); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  return { segments, loading, error };
}
