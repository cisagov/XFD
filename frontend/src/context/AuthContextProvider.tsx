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
import Cookies from 'universal-cookie';
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
    const domainEnv = import.meta.env.VITE_OKTA_COOKIE_DOMAIN as
      | string
      | undefined;
    return {
      path: '/',
      // Only set a domain attribute if NOT on localhost (cookie APIs treat localhost specially)
      domain: !isLocalhost && domainEnv ? domainEnv : undefined,
      secure: window.location.protocol === 'https:'
    } as const;
  }, []);

  const logout = useCallback(
    async (shouldReloadPage = true) => {
      setIsLoggingOut(true);

      try {
        // 1. Clear state first so usePersistentState flushes state cleanly
        setToken(null);
        setAuthUser(null);

        // 2. Clear storage explicitly
        localStorage.clear();

        // 3. Force-remove cookies across all variations
        cookies.remove('token', cookieOpts);
        cookies.remove('crossfeed-token', cookieOpts);
        cookies.remove('token', { path: '/' });
        cookies.remove('crossfeed-token', { path: '/' });

        // Extra safeguard: clear on window domain explicitly
        cookies.remove('token', {
          domain: window.location.hostname,
          path: '/'
        });
        cookies.remove('crossfeed-token', {
          domain: window.location.hostname,
          path: '/'
        });
      } catch (error) {
        logger.error(error);
      } finally {
        setIsLoggingOut(false);
        // Only reload if NOT redirecting elsewhere
        if (shouldReloadPage) {
          window.location.reload();
        }
      }
    },
    [cookies, cookieOpts, setToken]
  );

  const handleError = useCallback(
    async (
      in_error: Error & { statusCode?: number; response?: { status?: number } }
    ) => {
      logger.error(in_error);

      const statusCode = in_error.statusCode ?? in_error.response?.status;
      const isUnauthorized =
        statusCode === 401 || in_error.message?.includes('401');

      if (isUnauthorized) {
        await logout();
        const next = encodeURIComponent(window.location.pathname || '/');
        window.location.href = `${import.meta.env.VITE_API_URL}/saml/login?next=${next}`;
      }
    },
    [logout]
  );

  const api = useApi(handleError);
  const { apiGet } = api;

  const getProfile = useCallback(async () => {
    try {
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

      // Guard against non-error 401 payloads ({ detail: "Token has expired" })
      if (!user || !user.id) {
        throw new Error('401 Token has expired');
      }

      setAuthUser({
        ...user,
        isRegistered: user.first_name !== ''
      });
    } catch (err) {
      // Allow handleError to catch and perform cleanup
      setAuthUser(null);
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
  const refreshUser = useCallback(async () => {
    if (!token) return;
    await getProfile();
  }, [token, getProfile]);

  // Guard cookie sync against active logout cycles
  useEffect(() => {
    if (!token && !isLoggingOut) {
      const cookieToken =
        cookies.get('token') || cookies.get('crossfeed-token');
      if (cookieToken) {
        setToken(cookieToken);
      }
    }
  }, [token, cookies, isLoggingOut, setToken]);

  // Single effect for profile fetching when token changes
  useEffect(() => {
    if (!token) {
      setAuthUser(null);
    } else if (!authUser) {
      getProfile();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]); // Clean dependencies prevent infinite re-fetches

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
