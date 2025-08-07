import { AuthContextType } from 'context';
import {
  GLOBAL_ADMIN,
  GLOBAL_VIEW,
  REGIONAL_ADMIN,
  STANDARD_USER
} from './useUserLevel';
// import { GLOBAL_VIEW } from 'context/userStateUtils';
import { OrganizationShallow } from 'components/FilterDrawer/RegionAndOrganizationFilters';

export const REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS = false;

export const ORGANIZATION_EXCLUSIONS = ['dhs region'];

interface Filter {
  field: string;
  values: Array<any>;
  type: 'any' | 'all' | 'none';
}

type UseUserTypeFilters = (
  regions: string[],
  user: AuthContextType['user'],
  userLevel: number
) => Filter[];

export const useUserTypeFilters: UseUserTypeFilters = (
  regions,
  user,
  userLevel
) => {
  const userRoles = user?.roles ?? [];

  const userOrgs: OrganizationShallow[] =
    userRoles.length > 0
      ? userRoles
          .filter((role) => {
            let exclude = false;
            ORGANIZATION_EXCLUSIONS.forEach((item) => {
              if (role.organization.name.toLowerCase().includes(item)) {
                exclude = true;
              }
            });
            return !exclude;
          })
          .map((role) => {
            return {
              name: role?.organization?.name ?? '',
              id: role?.organization?.id ?? '',
              region_id: role?.organization?.region_id ?? '',
              root_domains: role?.organization?.root_domains ?? []
            };
          })
      : [];

  const userRegions = user?.region_id ? [user?.region_id] : [];

  switch (userLevel) {
    case STANDARD_USER:
      return [
        {
          field: 'organization.region_id',
          values: userRegions,
          type: 'any'
        },
        {
          field: 'organization_id',
          values: userOrgs,
          type: 'any'
        }
      ];
    case REGIONAL_ADMIN:
      return [
        {
          field: 'organization.region_id',
          values: REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS
            ? regions
            : userRegions,
          type: 'any'
        },
        {
          field: 'organization_id',
          values: [],
          type: 'any'
        }
      ];
    case GLOBAL_ADMIN:
      return [
        {
          field: 'organization.region_id',
          values: regions,
          type: 'any'
        },
        {
          field: 'organization_id',
          values: [],
          type: 'any'
        }
      ];
    case GLOBAL_VIEW:
      return [
        {
          field: 'organization.region_id',
          values: regions,
          type: 'any'
        },
        {
          field: 'organization_id',
          values: [],
          type: 'any'
        }
      ];

    default:
      return [];
      break;
  }
};
