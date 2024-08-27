import { AuthContextType, useAuthContext } from 'context';

export const GLOBAL_ADMIN = 3;
export const REGIONAL_ADMIN = 2;
export const STANDARD_USER = 1;

type UserType =
  | 'standard'
  | 'globalAdmin'
  | 'regionalAdmin'
  | 'globalView'
  | 'readySetCyber'
  | undefined
  | null;

type UserLevel = {
  userLevel: number;
  userType: UserType;
  user: AuthContextType['user'];
  formattedUserType: string;
};

export const useUserLevel: () => UserLevel = () => {
  const { user } = useAuthContext();
  let userLevel = 0;
  let formattedUserType = '';
  const userType: UserType = user?.userType;
  if (user && user.isRegistered) {
    if (user.userType === 'standard') {
      userLevel = STANDARD_USER;
      formattedUserType = 'Standard';
    } else if (user.userType === 'globalAdmin') {
      userLevel = GLOBAL_ADMIN;
      formattedUserType = 'Global Admin';
    } else if (
      user.userType === 'regionalAdmin' ||
      user.userType === 'globalView'
    ) {
      userLevel = REGIONAL_ADMIN;
      formattedUserType = 'Regional Admin';
    }
  }
  return {
    userLevel,
    userType,
    user,
    formattedUserType
  };
};
