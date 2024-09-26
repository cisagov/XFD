import { Organization, OrganizationTag } from 'types';
import { AuthUser, CurrentOrganization } from './AuthContext';
import { ORGANIZATION_EXCLUSIONS } from 'hooks/useUserTypeFilters';

const currentTermsVersion = process.env.REACT_APP_TERMS_VERSION;

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
  if (user?.userType === 'globalView') return 'user';
  return user && user.roles && user.roles.find((role) => role.role === 'admin')
    ? 'admin'
    : 'user';
};

export const getTouVersion = (maxRole: string) => {
  return `v${currentTermsVersion}-${maxRole}`;
};

export const getUserMustSign = (user: AuthUser | null, touVersion: string) => {
  return Boolean(
    !user?.dateAcceptedTerms ||
      (user.acceptedTermsVersion && user.acceptedTermsVersion !== touVersion)
  );
};

export const GLOBAL_VIEW = 2;
export const STANDARD_USER = 1;
export const ALL_USERS = GLOBAL_VIEW | STANDARD_USER;

//since allusers is called in feeds tsx, should we put this in the exported function?
//but then it would be declared each time the function is called, doesnt that seem funky?

export const getUserLevel = (user: AuthUser | null | undefined) => {
  let userLevel = 0;
  if (user && user.isRegistered) {
    if (user.userType === 'standard') {
      userLevel = STANDARD_USER;
    } else {
      userLevel = GLOBAL_VIEW;
    }
  }

  return userLevel;
};
