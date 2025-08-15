import React, { useEffect } from 'react';
import { useAuthContext } from 'context';
import { Button } from '@trussworks/react-uswds';
import { Alert, AlertTitle, Box, Grid, Typography } from '@mui/material';
import { CrossfeedWarning } from 'components/WarningBanner';
import { initialNotificationValues, MaintenanceNotification } from 'types';
import { v4 as uuidv4 } from 'uuid';
import pkceChallenge from 'pkce-challenge';

const LoginButton = () => {
  // TODO: Capture default values here once determined
  const domain = import.meta.env.VITE_COGNITO_DOMAIN || 'default_value';
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID || 'default_value';
  const callbackUrl =
    import.meta.env.VITE_COGNITO_CALLBACK_URL || 'default_value';

  const redirectToAuth = async () => {
    const { code_challenge, code_verifier } = await pkceChallenge();
    const state = uuidv4();

    try {
      await fetch(`${import.meta.env.VITE_API_URL}/auth/set-oauth-cookies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          code_verifier,
          state
        })
      });
      console.log('Cookies set, redirecting to Okta...');
      const authorizeUrl = `https://${domain}/oauth2/authorize?identity_provider=Okta&redirect_uri=${encodeURIComponent(
        callbackUrl
      )}&response_type=code&client_id=${clientId}&scope=email+openid+profile&state=${state}&code_challenge=${encodeURIComponent(
        code_challenge
      )}&code_challenge_method=S256`;

      window.location.href = authorizeUrl;
    } catch (err) {
      console.error('Error setting cookies before redirect:', err);
    }
  };

  return (
    <Button
      onClick={redirectToAuth}
      type={'button'}
      style={{ width: 'fit-content' }}
    >
      Sign in with LOGIN.GOV
    </Button>
  );
};

export const AuthLogin: React.FC<{ showSignUp?: boolean }> = () => {
  const { apiGet } = useAuthContext();
  const [notification, setNotification] =
    React.useState<MaintenanceNotification>(initialNotificationValues);
  const fetchNotifications = React.useCallback(async () => {
    try {
      const rows = await apiGet('/notifications');
      // Updated maintenance window banner check
      const now = new Date();
      const activeRow = rows.find((row: MaintenanceNotification) => {
        const start = new Date(row.start_datetime);
        const end = new Date(row.end_datetime);
        return row.status === 'active' && start <= now && now <= end;
      });
      setNotification(activeRow);
    } catch (e: any) {
      console.log(e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiGet]);
  useEffect(() => {
    fetchNotifications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const MaintenanceAlert: React.FC<any> = ({ notification }) => {
    // Determine the conditional title
    const isLoginUnavailable =
      notification?.maintenance_type === 'major' &&
      notification?.status === 'active';
    const titleText = isLoginUnavailable
      ? 'CyHy Dashboard Major Maintenance: Login Not Available'
      : 'CyHy Dashboard Maintenance Notification';

    return <AlertTitle>{titleText}</AlertTitle>;
  };

  const platformNotification = (
    <Grid size={{ xs: 12 }}>
      <Alert severity="warning">
        <MaintenanceAlert notification={notification} />
        {notification?.message}
      </Alert>
    </Grid>
  );
  return (
    <Box
      display="flex"
      flexDirection="column"
      justifyContent="space-around"
      height="100%"
    >
      {notification?.status === 'active' && platformNotification}
      <Typography variant="h2" textAlign="center" sx={{ mt: 5 }}>
        Welcome to CyHy Dashboard
      </Typography>
      <Box pt={3} mb={3} display="flex" justifyContent="center">
        <LoginButton />
      </Box>
      <CrossfeedWarning />
    </Box>
  );
};
