import { useAuthContext } from 'context';

type PostInit = {
  body?: unknown;
  showLoading?: boolean;
  headers?: HeadersInit;
  [key: string]: unknown;
};

export const usePostApi = () => {
  const { apiPost } = useAuthContext();

  return async <TResponse = unknown>(
    path: string,
    init: PostInit = {}
  ): Promise<TResponse> => {
    const result = await apiPost(path, init);
    return result as TResponse;
  };
};
