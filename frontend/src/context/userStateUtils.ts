import { Organization, OrganizationTag } from 'types';
import { AuthUser, CurrentOrganization } from './AuthContext';
import { ORGANIZATION_EXCLUSIONS } from 'hooks/useUserTypeFilters';

const currentTermsVersion = import.meta.env.VITE_TERMS_VERSION;

export const getExtendedOrg = (
  org: Organization | OrganizationTag | null,
  user: AuthUser | null
) => {
  const current: CurrentOrganization | null =
    org ?? user?.roles[0]?.organization ?? null;
  if (current && ORGANIZATION_EXCLUSIONS.includes(current?.name)) return null;
  return current;
};

export const getMaximumRole = (user: AuthUser | null) => {
  if (user?.user_type === 'globalView') return 'user';
  return user && user.roles && user.roles.find((role) => role.role === 'admin')
    ? 'admin'
    : 'user';
};

export const getTouVersion = (maxRole: string) => {
  return `v${currentTermsVersion}-${maxRole}`;
};

export const getUserMustSign = (user: AuthUser | null, touVersion: string) => {
  return Boolean(
    !user?.date_accepted_terms ||
    (user.accepted_terms_version && user.accepted_terms_version !== touVersion)
  );
};
