import { useCallback, useEffect, useRef, useState } from 'react';
import { isAbortError } from '../api/client';

interface ResourceState<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  isRefreshing: boolean;
  lastUpdatedAt: number | null;
}

export interface PollingResource<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  isRefreshing: boolean;
  lastUpdatedAt: number | null;
  refresh: () => void;
}

interface PollingOptions {
  intervalMs: number;
  enabled?: boolean;
  resetKey?: string | number | null;
}

function createInitialState<T>(isLoading: boolean): ResourceState<T> {
  return {
    data: null,
    error: null,
    isLoading,
    isRefreshing: false,
    lastUpdatedAt: null,
  };
}

function normalizeError(error: unknown): Error {
  return error instanceof Error ? error : new Error('An unexpected dashboard error occurred.');
}

/**
 * One bounded polling loop per resource.
 *
 * Guarantees:
 * - requests never overlap; a new request aborts the previous one
 * - polling pauses while the document is hidden and refreshes on return
 * - cleanup aborts in-flight work and clears the timer
 * - a resetKey change clears stale data before the next fetch
 */
export function usePollingResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  options: PollingOptions,
): PollingResource<T> {
  const { intervalMs, enabled = true, resetKey = null } = options;
  const [state, setState] = useState<ResourceState<T>>(() => createInitialState(enabled));
  const [refreshToken, setRefreshToken] = useState(0);
  const loadRef = useRef(load);
  const resetKeyRef = useRef<string | number | null>(resetKey);
  loadRef.current = load;

  const refresh = useCallback(() => {
    setRefreshToken((current) => current + 1);
  }, []);

  useEffect(() => {
    if (!enabled) {
      resetKeyRef.current = resetKey;
      setState(createInitialState(false));
      return;
    }

    const resetNeeded = resetKeyRef.current !== resetKey;
    if (resetNeeded) {
      resetKeyRef.current = resetKey;
    }
    setState((current) => (resetNeeded ? createInitialState(true) : current));

    let disposed = false;
    let activeController: AbortController | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let requestSequence = 0;
    let hasCompletedRequest = false;

    const clearTimer = () => {
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
      }
    };

    const scheduleNext = () => {
      if (disposed) {
        return;
      }
      clearTimer();
      timer = setTimeout(() => {
        timer = null;
        if (disposed) {
          return;
        }
        if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
          scheduleNext();
          return;
        }
        void runRequest();
      }, intervalMs);
    };

    const runRequest = async () => {
      if (disposed) {
        return;
      }

      clearTimer();
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;
      const sequence = ++requestSequence;

      setState((current) => ({
        ...current,
        isLoading: !hasCompletedRequest && current.data === null,
        isRefreshing: hasCompletedRequest || current.data !== null,
      }));

      try {
        const data = await loadRef.current(controller.signal);
        if (disposed || sequence !== requestSequence) {
          return;
        }
        hasCompletedRequest = true;
        setState({
          data,
          error: null,
          isLoading: false,
          isRefreshing: false,
          lastUpdatedAt: Date.now(),
        });
      } catch (error) {
        if (disposed || sequence !== requestSequence || isAbortError(error)) {
          return;
        }
        hasCompletedRequest = true;
        setState((current) => ({
          ...current,
          error: normalizeError(error),
          isLoading: false,
          isRefreshing: false,
        }));
      } finally {
        if (!disposed && sequence === requestSequence) {
          scheduleNext();
        }
      }
    };

    const handleVisibilityChange = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible' && !disposed) {
        void runRequest();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    void runRequest();

    return () => {
      disposed = true;
      requestSequence += 1;
      activeController?.abort();
      clearTimer();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [enabled, intervalMs, refreshToken, resetKey]);

  return {
    data: state.data,
    error: state.error,
    isLoading: state.isLoading,
    isRefreshing: state.isRefreshing,
    lastUpdatedAt: state.lastUpdatedAt,
    refresh,
  };
}
