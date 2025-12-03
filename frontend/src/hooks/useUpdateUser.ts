// hooks/useUpdateUser.ts
import { useApiPost } from './useApiPost';
import { ENDPOINTS } from '@/constants/endpoints';

export function useUpdateUser() {
  const { postData, isLoading, error } = useApiPost('Failed to update user.');

  const updateUser = async (userId: string | number, body: any) => {
    const endpoint = ENDPOINTS.USER_UPDATE_V2.replace(
      '{user_id}',
      String(userId)
    );
    return postData(endpoint, { body });
  };

  return {
    updateUser,
    isLoading,
    error
  };
}
