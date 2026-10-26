import { createContext, useCallback, useContext, useEffect, useMemo, useReducer } from 'react';
import { api } from '../services/api';

// Central client state. Everything dataset-specific is derived from the backend and
// discarded when a new dataset is uploaded (`datasetVersion` bumps so pages refetch).

export const STAGES = ['empty', 'uploaded', 'configured', 'analyzed', 'trained', 'predicted'];
export const atLeast = (stage, required) => STAGES.indexOf(stage) >= STAGES.indexOf(required);

const initialState = {
  status: 'loading',
  error: null,
  summary: { stage: 'empty' },
  analysis: null,
  metrics: null,
  datasetVersion: 0,
  resultsVersion: 0,
};

function reducer(state, action) {
  switch (action.type) {
    case 'loading':
      return { ...state, status: 'loading', error: null };
    case 'loaded':
      return { ...state, status: 'ready', error: null, summary: action.summary, analysis: action.analysis, metrics: action.metrics };
    case 'error':
      return { ...state, status: 'error', error: action.error };
    case 'reset':
      // Drop every dataset-specific artefact held in the browser.
      return { ...initialState, status: 'ready', datasetVersion: state.datasetVersion + 1, resultsVersion: state.resultsVersion + 1 };
    case 'summary':
      return { ...state, summary: action.summary };
    case 'analysis':
      return { ...state, analysis: action.analysis };
    case 'metrics':
      return { ...state, metrics: action.metrics, resultsVersion: state.resultsVersion + 1 };
    case 'config_changed':
      return { ...state, summary: action.summary, analysis: null, metrics: null, resultsVersion: state.resultsVersion + 1 };
    case 'results_changed':
      return { ...state, resultsVersion: state.resultsVersion + 1 };
    default:
      return state;
  }
}

const StoreContext = createContext(null);

async function loadAll() {
  const summary = await api.summary();
  let analysis = null;
  let metrics = null;
  if (summary.stage !== 'empty' && summary.analysis_available) {
    analysis = (await api.getAnalysis()).analysis;
  }
  if (atLeast(summary.stage, 'trained')) {
    metrics = (await api.metrics()).metrics;
  }
  return { summary, analysis, metrics };
}

export function AppStoreProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const refresh = useCallback(async () => {
    dispatch({ type: 'loading' });
    try {
      dispatch({ type: 'loaded', ...(await loadAll()) });
    } catch (error) {
      dispatch({ type: 'error', error });
    }
  }, []);

  const refreshSummary = useCallback(async () => {
    const summary = await api.summary();
    dispatch({ type: 'summary', summary });
    return summary;
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const actions = useMemo(() => ({
    refresh,
    refreshSummary,
    async uploadDataset(file) {
      const summary = await api.upload(file);
      dispatch({ type: 'reset' });
      dispatch({ type: 'summary', summary });
      return summary;
    },
    async confirmTarget(config) {
      const res = await api.confirmTarget(config);
      dispatch({ type: 'config_changed', summary: res.summary });
      return res;
    },
    async runAnalysis() {
      const res = await api.runAnalysis();
      dispatch({ type: 'analysis', analysis: res.analysis });
      await refreshSummary();
      return res.analysis;
    },
    async train(params) {
      const res = await api.train(params);
      dispatch({ type: 'metrics', metrics: res.metrics });
      await refreshSummary();
      return res.metrics;
    },
    async predict(body) {
      const res = await api.predict(body);
      dispatch({ type: 'results_changed' });
      await refreshSummary();
      return res;
    },
    async setThresholds(low, high) {
      const res = await api.setThresholds(low, high);
      await refreshSummary();
      dispatch({ type: 'results_changed' });
      return res;
    },
    async clearSession() {
      await api.deleteSession();
      dispatch({ type: 'reset' });
    },
  }), [refresh, refreshSummary]);

  const value = useMemo(() => ({ ...state, stage: state.summary?.stage || 'empty', ...actions }), [state, actions]);
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useAppStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useAppStore must be used inside AppStoreProvider');
  return ctx;
}
