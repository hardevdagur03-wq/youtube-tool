import { useCallback, useEffect, useRef, useState } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

type AsyncFn<T> = (signal: AbortSignal) => Promise<T>;

export function useApi<T>(
  fn: AsyncFn<T>,
  deps: unknown[] = [],
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const fnRef = useRef<AsyncFn<T>>(fn);
  fnRef.current = fn;

  const execute = useCallback(() => {
    setLoading(true);
    setError(null);

    const controller = new AbortController();

    fnRef.current(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          const msg = err instanceof Error ? err.message : 'An error occurred';
          setError(msg);
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [retryCount]);

  useEffect(() => {
    const cleanup = execute();
    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retryCount, ...deps]);

  const retry = useCallback(() => {
    setRetryCount((c) => c + 1);
  }, []);

  return { data, loading, error, retry };
}

export function useApiLazy<T>() {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const execute = useCallback(async (fn: AsyncFn<T>) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const result = await fn(controller.signal);
      if (!controller.signal.aborted) {
        setData(result);
        setLoading(false);
      }
      return result;
    } catch (err: unknown) {
      if (!controller.signal.aborted) {
        const msg = err instanceof Error ? err.message : 'An error occurred';
        setError(msg);
        setLoading(false);
      }
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    setData(null);
    setLoading(false);
    setError(null);
  }, []);

  return { data, loading, error, execute, reset };
}
