import { useCallback } from 'react';
import { usePostApi } from './usePostApi';
import { ENDPOINTS } from '@/constants/endpoints';

interface UpdateUserBody {
  userId: string;
  origin_path: 'user-registration' | 'user-management';
  body: {
    first_name?: string;
    last_name?: string;
    user_type?: string;
    email?: string;
    state?: string;
    region_id?: string;
    invite_pending?: boolean;
  };
}

export const useUpdateUser = () => {
  const apiPost = usePostApi();

  const updateUser = useCallback(
    async ({ userId, origin_path, body }: UpdateUserBody): Promise<void> => {
      const path = ENDPOINTS.USER_UPDATE_V2.replace('{user_id}', userId);

      await apiPost(path, {
        body,
        headers: {
          'X-Origin-Path': origin_path
        }
      });
    },
    [apiPost]
  );

  return { updateUser };
};
