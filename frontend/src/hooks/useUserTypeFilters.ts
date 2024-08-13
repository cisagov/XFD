import { AuthContextType } from 'context';
import { GLOBAL_ADMIN, REGIONAL_ADMIN, STANDARD_USER } from './useUserLevel';
import { GLOBAL_VIEW } from 'context/userStateUtils';
import { OrganizationShallow } from 'components/OrganizationSearch';

export const REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS = true;

interface Filter {
  field: string;
  values: Array<any>;
  type: 'any' | 'all' | 'none';
}
type AddFilter = (
  field: Filter['field'],
  value: any,
  type: Filter['type']
) => void;
type RemoveFilter = AddFilter;

type UseUserTypeFilters = (
  filters: Filter[],
  addFilter: AddFilter,
  removeFilter: RemoveFilter,
  regions: string[],
  user: AuthContextType['user'],
  userLevel: number
) => Filter[];

export const useUserTypeFilters: UseUserTypeFilters = (
  filters,
  addFilter,
  removeFilter,
  regions,
  user,
  userLevel
) => {
  const userRoles = user?.roles ?? [];

  const userOrgs: OrganizationShallow[] =
    userRoles.length > 0
      ? userRoles.map((role) => {
          return {
            name: role?.organization?.name ?? '',
            id: role?.organization?.id ?? '',
            regionId: role?.organization?.regionId ?? '',
            rootDomains: role?.organization?.rootDomains ?? []
          };
        })
      : [];

  const userRegions = user?.regionId ? [user?.regionId] : [];

  switch (userLevel) {
    case STANDARD_USER:
      return [
        {
          field: 'organization.regionId',
          values: userRegions,
          type: 'any'
        },
        {
          field: 'organizationId',
          values: userOrgs,
          type: 'any'
        }
      ];
    case REGIONAL_ADMIN:
      return [
        {
          field: 'organization.regionId',
          values: REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS
            ? regions
            : userRegions,
          type: 'any'
        },
        {
          field: 'organizationId',
          values: userOrgs,
          type: 'any'
        }
      ];

      break;
    case GLOBAL_ADMIN:
      return [];
      break;
    case GLOBAL_VIEW:
      return [];
      break;

    default:
      return [];
      break;
  }
};
