import { useAuthContext } from 'context';

type GetInit = {
  showLoading?: boolean;
  headers?: HeadersInit;
  [key: string]: unknown;
};

export const useGetApi = () => {
  const { apiGet } = useAuthContext();

  return async <TResponse = unknown>(
    path: string,
    init: GetInit = {}
  ): Promise<TResponse> => {
    const result = await apiGet(path, init);
    return result as TResponse;
  };
};
