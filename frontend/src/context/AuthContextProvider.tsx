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
  // const [token, setToken] = usePersistentState<string | null>('token', null);

  // const token = null; // legacy compat, but stop using it
  // const setToken = useCallback(() => {}, []); // legacy compat, but stop using it
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

  // Single cookies instance for the lifetime of the provider
  // const cookies = useMemo(() => new Cookies(), []);

  // Compute cookie options that work both locally and in prod
  // const cookieOpts = useMemo(() => {
  //   const isLocalhost =
  //     window.location.hostname === 'localhost' ||
  //     window.location.hostname === '127.0.0.1';
  //   const domainEnv = import.meta.env.VITE_OKTA_COOKIE_DOMAIN as
  //     | string
  //     | undefined;
  //   return {
  //     path: '/',
  //     // Only set a domain attribute if NOT on localhost (cookie APIs treat localhost specially)
  //     domain: !isLocalhost && domainEnv ? domainEnv : undefined,
  //     secure: window.location.protocol === 'https:'
  //   } as const;
  // }, []);

  const login = useCallback((nextPath?: string) => {
    const next = encodeURIComponent(
      nextPath ?? window.location.pathname ?? '/'
    );
    window.location.href = `${import.meta.env.VITE_API_URL}/saml/login?next=${next}`;
  }, []);

  // const logout = useCallback(async () => {
  //   setIsLoggingOut(true);

  //   // If the user has a token, reload at the end to reset app state
  //   const shouldReload = !!token;

  //   try {
  //     // Clear local storage and Amplify session (if any)
  //     localStorage.clear();

  //     // Remove both cookies the backend may have set
  //     cookies.remove('token', cookieOpts);
  //     cookies.remove('crossfeed-token', cookieOpts);

  //     // Clear in-memory state
  //     setAuthUser(null);
  //     setToken(null);
  //   } catch (error) {
  //     logger.error(error);
  //   } finally {
  //     setIsLoggingOut(false);
  //     if (shouldReload) {
  //       window.location.reload();
  //     }
  //   }
  // }, [cookies, cookieOpts, setToken, token]);
  const logout = useCallback(async () => {
    setIsLoggingOut(true);

    try {
      // remove only auth artifacts if you still had any legacy ones
      // localStorage.removeItem('token');

      // Best: call backend logout endpoint so it deletes cookies using the same domain/path attributes
      // (if you have it accessible from SPA)
      try {
        // window.location.href = `${import.meta.env.VITE_API_URL}/saml/logout?next=/settings`;
        window.location.href = `${import.meta.env.VITE_API_URL}/saml/logout?next=/`;
        return; // redirecting away
      } catch {
        // fallback to client-side cookie removal
      }

      setAuthUser(null);
    } finally {
      setIsLoggingOut(false);
    }
    // }, [cookies, cookieOpts]);
  }, []);

  const handleError = useCallback(async (in_error: Error) => {
    logger.error(in_error);
    if (in_error.message.includes('401')) {
      // Have to remove because it auto logs back in on logout and creates a loop.
      // console.log(`AuthContextProvider: 401 detected, logging out ${in_error}`);
      // await logout();
      // const next = encodeURIComponent(window.location.pathname || '/');
      // window.location.href = `${import.meta.env.VITE_API_URL}/saml/login?next=${next}`;
    }
  }, []);

  const api = useApi(handleError);
  const { apiGet } = api;

  const getProfile = useCallback(async () => {
    // const user: User = await apiGet<User>(ENDPOINTS.USERS_ME);

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

    //   setAuthUser({
    //     ...user,
    //     isRegistered: user.first_name !== ''
    //   });
    // }, [apiGet]);
    try {
      const user: User = await apiGet<User>(ENDPOINTS.USERS_ME);

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
      setAuthUser({
        ...user,
        isRegistered: user.first_name !== ''
      });
    },
    [setAuthUser]
  );

  // New, SAML-only "refresh": just refetch the profile if we already have a token
  // const refreshUser = useCallback(async () => {
  //   if (!token) return;
  //   await getProfile();
  // }, [token, getProfile]);
  const refreshUser = useCallback(async () => {
    setAuthLoading(true);
    await getProfile();
  }, [getProfile]);

  // SPA token update from cookies after SAML ACS redirect
  // useEffect(() => {
  //   if (!token) {
  //     const cookieToken =
  //       cookies.get('token') || cookies.get('crossfeed-token');
  //     if (cookieToken) {
  //       // Set token from cookie if we don't have one yet
  //       setToken(cookieToken);
  //     }
  //   }
  //   // eslint-disable-next-line react-hooks/exhaustive-deps
  // }, [token, cookies]);

  // On first mount, refresh user
  useEffect(() => {
    refreshUser();
    setAuthLoading(true);
    // getProfile().catch(() => {
    //   // if 401, handleError will redirect; still ensure authLoading ends
    //   setAuthLoading(false);
    // });
    // eslint-disable-next-line
  }, []);

  // When token changes, either clear user or fetch profile
  // useEffect(() => {
  // //   if (!token) {
  // //     setAuthUser(null);
  // //   } else {
  // //     getProfile();
  // //   }
  // // }, [token, getProfile]);
  //   setAuthLoading(true);
  //   getProfile().catch(() => {
  //     // if 401, handleError will redirect; still ensure authLoading ends
  //     setAuthLoading(false);
  //   });
  //   // eslint-disable-next-line
  // }, []);

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
        // token,
        loading: authLoading,
        setUser: setProfile,
        refreshUser,
        setOrganization: setOrg,
        showMaps: showMap,
        setShowMaps: setShowMap,
        currentOrganization: extendedOrg,
        showAllOrganizations: showAllOrganizations,
        setShowAllOrganizations: setShowAllOrganizations,
        // login: setToken,
        login,
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
