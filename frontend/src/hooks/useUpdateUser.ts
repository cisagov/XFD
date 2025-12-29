import { usePostApi } from './usePostApi';
import { ENDPOINTS } from '@/constants/endpoints';

type UpdateUserBody = {
  first_name?: string;
  last_name?: string;
  user_type?: string;
  email?: string;
  state: string;
  region_id: string;
};

type UseUpdateUserResult = {
  updateUser: (userId: string | number, body: UpdateUserBody) => Promise<void>;
};

export const useUpdateUser = (): UseUpdateUserResult => {
  const postApi = usePostApi();

  const updateUser = async (
    userId: string | number,
    body: UpdateUserBody
  ): Promise<void> => {
    const path = ENDPOINTS.USER_UPDATE_V2.replace('{user_id}', String(userId));
    await postApi(path, { body });
  };

  return { updateUser };
};
