import { usePostApi } from './usePostApi';
import { ENDPOINTS } from '@/constants/endpoints';

type UseAddUserToOrganizationResult = {
  addUserToOrganization: (
    organizationId: string | number,
    userId: string | number,
    role: string
  ) => Promise<void>;
};

export const useAddUserToOrganization = (): UseAddUserToOrganizationResult => {
  const postApi = usePostApi();

  const addUserToOrganization = async (
    organizationId: string | number,
    userId: string | number,
    role: string
  ): Promise<void> => {
    const path = ENDPOINTS.ORGANIZATION_ADD_USER.replace(
      '{organization_id}',
      String(organizationId)
    );

    await postApi(path, {
      body: { user_id: userId, role }
    });
  };

  return { addUserToOrganization };
};
