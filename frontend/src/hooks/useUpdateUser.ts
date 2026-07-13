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
  onSuccess?: () => Promise<void> | void;
  onError?: (errorMessage: string) => void;
}

export const useUpdateUser = () => {
  const apiPost = usePostApi();

  const updateUser = useCallback(
    async ({
      userId,
      origin_path,
      body,
      onSuccess,
      onError
    }: UpdateUserBody): Promise<{ success: boolean; body: string }> => {
      try {
        const path = ENDPOINTS.USER_UPDATE_V2.replace('{user_id}', userId);
        await apiPost(path, {
          body,
          headers: {
            'X-Origin-Path': origin_path
          }
        });

        if (onSuccess) {
          await onSuccess();
        }

        return { success: true, body: 'User profile successfully updated.' };
      } catch (e: any) {
        if (onError) {
          onError(e.message);
        }
        return { success: false, body: e.message };
      }
    },
    [apiPost]
  );

  return { updateUser };
};
