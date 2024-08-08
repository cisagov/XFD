import { useAuthContext } from 'context';

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
};

export const useUserLevel: () => UserLevel = () => {
  const { user } = useAuthContext();
  let userLevel = 0;
  const userType: UserType = user?.userType;
  if (user && user.isRegistered) {
    if (user.userType === 'standard') {
      userLevel = STANDARD_USER;
    } else if (user.userType === 'globalAdmin') {
      userLevel = GLOBAL_ADMIN;
    } else if (
      user.userType === 'regionalAdmin' ||
      user.userType === 'globalView'
    ) {
      userLevel = REGIONAL_ADMIN;
    }
  }
  return {
    userLevel,
    userType
  };
};
