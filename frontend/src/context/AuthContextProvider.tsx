// frontend/src/context/AuthContextProvider.tsx
import React, { useState, useCallback, useEffect, useMemo } from 'react';
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
import Cookies from 'universal-cookie';
import { Snackbar } from '@mui/material';
import { Alert } from '@mui/material';
import { AlertProps } from '@mui/material/Alert';
import { ENDPOINTS } from '@/constants/endpoints';

export const currentTermsVersion = '1';

interface AuthContextProviderProps {
  children: React.ReactNode;
}

export const AuthContextProvider: React.FC<AuthContextProviderProps> = ({
  children
}) => {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [token, setToken] = usePersistentState<string | null>('token', null);
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

  // Single cookies instance for the lifetime of the provider
  const cookies = useMemo(() => new Cookies(), []);

  // Compute cookie options that work both locally and in prod
  const cookieOpts = useMemo(() => {
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1';
    const domainEnv = import.meta.env.VITE_COOKIE_DOMAIN as string | undefined;
    return {
      path: '/',
      // Only set a domain attribute if NOT on localhost (cookie APIs treat localhost specially)
      domain: !isLocalhost && domainEnv ? domainEnv : undefined,
      secure: window.location.protocol === 'https:'
    } as const;
  }, []);

  const logout = useCallback(async () => {
    setIsLoggingOut(true);

    // If the user has a token, reload at the end to reset app state
    const shouldReload = !!token;

    try {
      // Clear local storage and Amplify session (if any)
      localStorage.clear();

      // Remove both cookies the backend may have set
      cookies.remove('token', cookieOpts);
      cookies.remove('crossfeed-token', cookieOpts);

      // Clear in-memory state
      setAuthUser(null);
      setToken(null);
    } finally {
      setIsLoggingOut(false);
      if (shouldReload) {
        window.location.reload();
      }
    }
  }, [cookies, cookieOpts, setToken, token]);

  const handleError = useCallback(
    async (in_error: Error) => {
      if (in_error.message.includes('401')) {
        await logout();
        const next = encodeURIComponent(window.location.pathname || '/');
        window.location.href = `${import.meta.env.VITE_API_URL}/saml/login?next=${next}`;
      }
    },
    [logout]
  );

  const api = useApi(handleError);
  const { apiGet, apiPost } = api;

  const getProfile = useCallback(async () => {
    const user: User = await apiGet<User>(ENDPOINTS.USERS_ME);

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

    setAuthUser({
      ...user,
      isRegistered: user.first_name !== ''
    });
  }, [apiGet]);

  const setProfile = useCallback(
    async (user: User) => {
      setAuthUser({
        ...user,
        isRegistered: user.first_name !== ''
      });
    },
    [setAuthUser]
  );

  // New, SAML-only "refresh": just refetch the profile if we already have a token
  const refreshUser = useCallback(async () => {
    if (!token) return;
    await getProfile();
  }, [token, getProfile]);

  // SPA token update from cookies after SAML ACS redirect
  useEffect(() => {
    if (!token) {
      const cookieToken =
        cookies.get('token') || cookies.get('crossfeed-token');
      if (cookieToken) {
        // Set token from cookie if we don't have one yet
        setToken(cookieToken);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, cookies]);

  // On first mount, try Cognito refresh (if enabled)
  useEffect(() => {
    refreshUser();
    // eslint-disable-next-line
  }, []);

  // When token changes, either clear user or fetch profile
  useEffect(() => {
    if (!token) {
      setAuthUser(null);
    } else {
      getProfile();
    }
  }, [token, getProfile]);

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
        user: authUser,
        token,
        setUser: setProfile,
        refreshUser,
        setOrganization: setOrg,
        showMaps: showMap,
        setShowMaps: setShowMap,
        currentOrganization: extendedOrg,
        showAllOrganizations: showAllOrganizations,
        setShowAllOrganizations: setShowAllOrganizations,
        login: setToken,
        logout,
        setLoading: () => {},
        maximumRole,
        touVersion,
        userMustSign,
        setFeedbackMessage,
        user_type: '',
        isLoggingOut,
        ...api
      }}
    >
      {api.loading && (
        <div className="cisa-crossfeed-loading">
          <div></div>
          <div></div>
        </div>
      )}
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
