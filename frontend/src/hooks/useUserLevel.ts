import { AuthContextType, useAuthContext } from 'context';

export const GLOBAL_ADMIN = 4;
export const GLOBAL_VIEW = 3;
export const REGIONAL_ADMIN = 2;
export const STANDARD_USER = 1;

type UserType =
  | 'standard'
  | 'globalAdmin'
  | 'regionalAdmin'
  | 'globalView'
  | undefined
  | null;

type UserLevel = {
  userLevel: number;
  user_type: UserType;
  user: AuthContextType['user'];
  formattedUserType: string;
};

export const useUserLevel: () => UserLevel = () => {
  const { user } = useAuthContext();
  let userLevel = 0;
  let formattedUserType = '';
  const user_type: UserType = user?.user_type;
  if (user && user.isRegistered) {
    if (user.user_type === 'standard') {
      userLevel = STANDARD_USER;
      formattedUserType = 'Standard User';
    } else if (user.user_type === 'globalAdmin') {
      userLevel = GLOBAL_ADMIN;
      formattedUserType = 'Global Admin';
    } else if (user.user_type === 'regionalAdmin') {
      userLevel = REGIONAL_ADMIN;
      formattedUserType = 'Regional Admin';
    } else if (user.user_type === 'globalView') {
      userLevel = GLOBAL_VIEW;
      formattedUserType = 'Global View';
    }
  }
  return {
    userLevel,
    user_type,
    user,
    formattedUserType
  };
};
