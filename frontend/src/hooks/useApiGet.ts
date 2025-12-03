import { useState, useEffect, useCallback } from 'react';
import { useAuthContext } from '@/context/AuthContext';

/**
 * Generic hook for GET requests using apiGet from auth context.
 *
 * @param endpoint - the URL or template string for the GET call
 * @param deps - any dependencies that should trigger refetch
 */
export function useApiGet<T extends object>(
  endpoint: string | null,
  deps: any[] = [],
  customErrorMessage?: string
) {
  const { apiGet } = useAuthContext();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!endpoint) {
      setData(null);
      return;
    }
    setIsLoading(true);
    try {
      const response = await apiGet<T>(endpoint);
      setData(response);
      setError('');
    } catch (e: any) {
      const message = e.message + ('. ' + e.response?.data?.detail || '');
      setError(
        customErrorMessage ? customErrorMessage + ' ' + message : message
      );
    } finally {
      setIsLoading(false);
    }
  }, [apiGet, endpoint]);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return {
    data,
    error,
    isLoading,
    refetch: fetchData
  };
}
