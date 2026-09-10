import { useState, useCallback, useRef, useEffect } from 'react';
import type { V3ExportProgress, V3ExportResult } from '../types';
import { unwrapResponse } from '../services/apiClient';

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE) || '';
const POLL_INTERVAL = 1000;
const MAX_CONSECUTIVE_ERRORS = 5;
const POLL_TIMEOUT_MS = 300_000;
const HEALTH_RETRY_DELAYS = [500, 1000, 2000, 3000, 5000];

function describeFetchError(err: unknown, status?: number): string {
  if (err instanceof DOMException && err.name === 'AbortError') {
    return 'Request timed out. The server may be overloaded. Please try again.';
  }
  if (err instanceof TypeError) {
    const msg = err.message;
    if (msg === 'Failed to fetch' || msg.includes('NetworkError')) {
      return 'Unable to connect to the server. Make sure the backend is running.';
    }
  }
  if (status) {
    if (status === 0) return 'Unable to connect to the server.';
    if (status === 429) return 'Too many requests. Please wait a moment.';
    if (status >= 500) return 'Server encountered an internal error. Please try again later.';
    return `Server returned an error (HTTP ${status}).`;
  }
  if (err instanceof Error) {
    const msg = err.message;
    if (msg.includes('quota') || msg.includes('quotaExceeded')) {
      return 'YouTube API quota exceeded. Please try again later.';
    }
    if (msg.includes('not found')) {
      return 'The requested channel or video was not found. Check the URL and try again.';
    }
    if (msg.includes('connection') || msg.includes('timeout')) {
      return 'Unable to connect to the server. Make sure the backend is running.';
    }
    return msg;
  }
  return 'An unexpected error occurred. Please try again.';
}

export function useExport() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<V3ExportProgress | null>(null);
  const [result, setResult] = useState<V3ExportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<number | null>(null);
  const healthPollRef = useRef<number | null>(null);
  const [backendStatus, setBackendStatus] = useState<'unknown' | 'ok' | 'error'>('unknown');

  // Persistent backend health polling — runs every 15s to update status indicator
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/health`);
        if (resp.ok) {
          const data = await resp.json();
          const health = unwrapResponse<{ status: string }>(data);
          setBackendStatus(health.status === 'ok' ? 'ok' : 'error');
        } else {
          setBackendStatus('error');
        }
      } catch {
        setBackendStatus('error');
      }
    };
    checkHealth();
    healthPollRef.current = window.setInterval(checkHealth, 15000);
    return () => {
      if (healthPollRef.current !== null) clearInterval(healthPollRef.current);
    };
  }, []);

  const checkHealthWithRetry = useCallback(async (): Promise<boolean> => {
    for (const delay of HEALTH_RETRY_DELAYS) {
      try {
        const resp = await fetch(`${API_BASE}/api/health`);
        if (resp.ok) {
          const data = await resp.json();
          const health = unwrapResponse<{ status: string; youtube_api_key_error?: string }>(data);
          if (health.status === 'ok') {
            setBackendStatus('ok');
            return true;
          }
          setError(health.youtube_api_key_error || 'Backend is in degraded state.');
          setBackendStatus('error');
          return false;
        }
      } catch {
        // Backend not ready yet — retry after delay
      }
      await new Promise(r => setTimeout(r, delay));
    }
    setBackendStatus('error');
    return false;
  }, []);

  const pollProgress = useCallback((id: string) => {
    let consecutiveErrors = 0;
    const startedAt = Date.now();
    const poll = async () => {
      if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
        setError('Export timed out. The channel may have too many videos. Try a smaller limit.');
        setLoading(false);
        return;
      }
      try {
        const resp = await fetch(`${API_BASE}/api/export/${id}/progress`);
        if (!resp.ok) {
          consecutiveErrors++;
          if (consecutiveErrors > MAX_CONSECUTIVE_ERRORS) {
            setError('Failed to check export progress. The server may have restarted.');
            setLoading(false);
            return;
          }
          pollingRef.current = window.setTimeout(poll, POLL_INTERVAL * 2);
          return;
        }
        consecutiveErrors = 0;
        const body = await resp.json();
        const data: V3ExportProgress = unwrapResponse<V3ExportProgress>(body);
        setProgress(data);
        setLoading(false);

        if (data.status === 'completed') {
          let tries = 0;
          const fetchResult = async (): Promise<void> => {
            try {
              const resultResp = await fetch(`${API_BASE}/api/export/${id}/result`);
              if (resultResp.ok) {
                const resultBody = await resultResp.json();
                const resultData: V3ExportResult = unwrapResponse<V3ExportResult>(resultBody);
                if (resultData.result) {
                  setResult(resultData);
                  return;
                }
              }
            } catch { /* retry */ }
            if (tries++ < 5) {
              await new Promise(r => setTimeout(r, 500));
              return fetchResult();
            }
            setError('Export completed but result is not ready. Please refresh.');
            setLoading(false);
          };
          fetchResult();
          return;
        }
        if (data.status === 'failed') {
          setError(data.error || 'Export failed.');
          return;
        }
        if (data.status === 'cancelled') {
          setError('Export was cancelled.');
          return;
        }
        pollingRef.current = window.setTimeout(poll, POLL_INTERVAL);
      } catch {
        consecutiveErrors++;
        if (consecutiveErrors > MAX_CONSECUTIVE_ERRORS) {
          setError('Lost connection to the server while checking progress.');
          setLoading(false);
          return;
        }
        pollingRef.current = window.setTimeout(poll, POLL_INTERVAL * 2);
      }
    };
    poll();
  }, []);

  const startExport = useCallback(async (channel: string, limit: number) => {
    setLoading(true);
    setError(null);
    setProgress(null);
    setResult(null);

    const healthy = await checkHealthWithRetry();
    if (!healthy) {
      setLoading(false);
      return;
    }

    try {
      const resp = await fetch(`${API_BASE}/api/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel, limit }),
      });
      if (!resp.ok) {
        let detail = '';
        try { const body = await resp.json(); detail = body.message || body?.errors?.[0]?.detail || ''; } catch { /* ignore */ }
        throw new Error(detail || `Server error (HTTP ${resp.status})`);
      }
      const body = await resp.json();
      const exportData = unwrapResponse<{ job_id: string }>(body);
      if (!exportData.job_id) throw new Error('Server did not return a job ID.');
      setJobId(exportData.job_id);
      pollProgress(exportData.job_id);
    } catch (err: any) {
      setError(describeFetchError(err, (err as any)?.status));
      setLoading(false);
    }
  }, [checkHealthWithRetry, pollProgress]);

  const cancelExport = useCallback(async () => {
    if (!jobId) return;
    try {
      const resp = await fetch(`${API_BASE}/api/export/${jobId}/cancel`, { method: 'POST' });
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        throw new Error(body?.error || `Server returned ${resp.status}`);
      }
      setError('Export cancelled.');
      setLoading(false);
    } catch {
      setError('Failed to cancel export.');
    }
  }, [jobId]);

  const reset = useCallback(() => {
    if (pollingRef.current !== null) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
    setJobId(null);
    setProgress(null);
    setResult(null);
    setLoading(false);
    setError(null);
    setBackendStatus('unknown');
  }, []);

  const retry = useCallback(() => {
    reset();
  }, [reset]);

  return {
    jobId,
    progress,
    result,
    loading,
    error,
    startExport,
    cancelExport,
    reset,
    retry,
    backendStatus,
  };
}
