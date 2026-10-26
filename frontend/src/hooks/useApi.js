import { useCallback, useEffect, useRef, useState } from 'react';

// Runs `fetcher` whenever `deps` change (and `enabled` is true). Returns data/loading/error/reload.
export function useApiData(fetcher, deps, enabled = true) {
  const [state, setState] = useState({ data: null, loading: enabled, error: null });
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, loading: false, error: null });
      return undefined;
    }
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcherRef.current()
      .then((data) => !cancelled && setState({ data, loading: false, error: null }))
      .catch((error) => !cancelled && setState({ data: null, loading: false, error }));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, reload, setData: (data) => setState((s) => ({ ...s, data })) };
}

// Wraps an async action with pending/error state for buttons.
export function useAction(action) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const run = useCallback(async (...args) => {
    setPending(true);
    setError(null);
    try {
      return await action(...args);
    } catch (err) {
      setError(err);
      return undefined;
    } finally {
      setPending(false);
    }
  }, [action]);
  return { run, pending, error, clearError: () => setError(null) };
}
