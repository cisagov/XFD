// hooks/useApiPost.ts
import { useState, useCallback } from 'react';
import { useAuthContext } from '@/context/AuthContext';

export function useApiPost<T extends object = any>(
  customErrorMessage?: string
) {
  const { apiPost } = useAuthContext();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const postData = useCallback(
    async (endpoint: string, options: any = {}): Promise<T | null> => {
      setIsLoading(true);
      try {
        const result = await apiPost<T>(endpoint, options);
        setError('');
        return result;
      } catch (e: any) {
        const message = e.message + ('. ' + e.response?.data?.detail || '');
        setError(
          customErrorMessage ? customErrorMessage + ' ' + message : message
        );
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    [apiPost]
  );

  return { postData, isLoading, error };
}
