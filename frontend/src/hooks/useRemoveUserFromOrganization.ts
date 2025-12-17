import { usePostApi } from './usePostApi';
import { ENDPOINTS } from '@/constants/endpoints';

type UseRemoveUserFromOrganizationResult = {
  removeUserFromOrganization: (
    organizationId: string | number,
    roleId: string | number
  ) => Promise<void>;
};

export const useRemoveUserFromOrganization =
  (): UseRemoveUserFromOrganizationResult => {
    const postApi = usePostApi();

    const removeUserFromOrganization = async (
      organizationId: string | number,
      roleId: string | number
    ): Promise<void> => {
      const path = ENDPOINTS.ORGANIZATION_REMOVE_ROLE.replace(
        '{organization_id}',
        String(organizationId)
      ).replace('{role_id}', String(roleId));

      await postApi(path, { body: {} });
    };

    return { removeUserFromOrganization };
  };
