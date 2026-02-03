// frontend/src/context/AuthContextProvider.tsx
import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { logger } from '@/utils/logger';
import Alert, { AlertProps } from '@mui/material/Alert';
import Snackbar from '@mui/material/Snackbar';
import { AuthContext, AuthUser } from './AuthContext';
import { User, Organization, OrganizationTag } from 'types';
import { useApi } from 'hooks/useApi';
import { usePersistentState } from 'hooks';
import {
  getExtendedOrg,
  getMaximumRole,
  getTouVersion,
  getUserMustSign
} from './userStateUtils';
import { ENDPOINTS } from '@/constants/endpoints';

export const currentTermsVersion = '1';

interface AuthContextProviderProps {
  children: React.ReactNode;
}

export const AuthContextProvider: React.FC<AuthContextProviderProps> = ({
  children
}) => {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [org, setOrg] = usePersistentState<
    Organization | OrganizationTag | null
  >('organization', null);
  const [showMap, setShowMap] = usePersistentState<boolean>('showMap', false);
  const [showAllOrganizations, setShowAllOrganizations] =
    usePersistentState<boolean>('showAllOrganizations', false);
  const [feedbackMessage, setFeedbackMessage] = useState<{
    message: string;
    type: AlertProps['severity'];
  } | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const login = useCallback((nextPath?: string) => {
    const next = encodeURIComponent(
      nextPath ?? window.location.pathname ?? '/'
    );
    window.location.href = `${import.meta.env.VITE_API_URL}/saml/login?next=${next}`;
  }, []);

  const logout = useCallback(async () => {
    setIsLoggingOut(true);

    try {
      try {
        window.location.href = `${import.meta.env.VITE_API_URL}/saml/logout?next=/`;
        return; // redirecting to logout
      } catch {
        // Catch any errors from redirecting - Add logic if needed.
      }
      setAuthUser(null);
    } finally {
      setIsLoggingOut(false);
    }
  }, []);

  const handleError = useCallback(async (in_error: Error) => {
    logger.error(in_error);
    if (in_error.message.includes('401')) {
    }
  }, []);

  const api = useApi(handleError);
  const { apiGet } = api;

  const getProfile = useCallback(async () => {
    // TODO: Uncomment this if we want to fully disable logins during maintenance windows.
    // Currently commented to meet "waiting room" needs and allow login for state selection
    // and user terms acceptance for new users.
    //
    // This acts as a backup safeguard to alert users login is unavailable and log them out.
    // If user is blocked due to maintenance, show alert and logout.
    //
    // if (user.login_blocked_by_maintenance) {
    //   alert(
    //     'Product has not officially been launched. Please check back again.'
    //   );
    //   await logout();
    //   return;
    // }

    try {
      const user: User = await apiGet<User>(ENDPOINTS.USERS_ME);
      if (!user) {
        logger.warn('getProfile received empty user object');
        setAuthUser(null);
        return;
      }
      setAuthUser({
        ...user,
        isRegistered: user.first_name !== ''
      });
    } finally {
      setAuthLoading(false);
    }
  }, [apiGet]);

  const setProfile = useCallback(
    async (user: User) => {
      if (!user) {
        logger.warn('setProfile called with undefined user');
        setAuthUser(null);
        return;
      }
      setAuthUser({
        ...user,
        isRegistered: user.first_name !== ''
      });
    },
    [setAuthUser]
  );

  // New, SAML-only "refresh": just refetch the profile if we already have a token
  const refreshUser = useCallback(async () => {
    setAuthLoading(true);
    await getProfile();
  }, [getProfile]);

  // On first mount, refresh user
  useEffect(() => {
    refreshUser();
    setAuthLoading(true);
    // eslint-disable-next-line
  }, []);

  const extendedOrg = useMemo(
    () => getExtendedOrg(org, authUser),
    [org, authUser]
  );
  const maximumRole = useMemo(() => getMaximumRole(authUser), [authUser]);
  const touVersion = useMemo(() => getTouVersion(maximumRole), [maximumRole]);
  const userMustSign = useMemo(
    () => getUserMustSign(authUser, touVersion),
    [authUser, touVersion]
  );

  return (
    <AuthContext.Provider
      value={{
        ...api,
        user: authUser,
        loading: authLoading || api.loading,
        setUser: setProfile,
        refreshUser,
        setOrganization: setOrg,
        showMaps: showMap,
        setShowMaps: setShowMap,
        currentOrganization: extendedOrg,
        showAllOrganizations: showAllOrganizations,
        setShowAllOrganizations: setShowAllOrganizations,
        login,
        logout,
        setLoading: () => {},
        maximumRole,
        touVersion,
        userMustSign,
        setFeedbackMessage,
        user_type: '',
        isLoggingOut
      }}
    >
      {api.loading ||
        (authLoading && (
          <div className="cisa-crossfeed-loading">
            <div></div>
            <div></div>
          </div>
        ))}
      {feedbackMessage && (
        <Snackbar
          open={!!feedbackMessage}
          autoHideDuration={5000}
          onClose={() => setFeedbackMessage(null)}
        >
          <Alert
            onClose={() => setFeedbackMessage(null)}
            severity={feedbackMessage.type}
          >
            {feedbackMessage.message}
          </Alert>
        </Snackbar>
      )}
      {children}
    </AuthContext.Provider>
  );
};
