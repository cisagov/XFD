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
    const devToken = 'dev-fake-token';

    // Add a dummy signedToken so OktaCallback doesn't fail
    localStorage.setItem('oauthMeta', 'dev-signed-token');

    // Optional: simulate /users/me response
    localStorage.setItem(
      'mockUser',
      JSON.stringify({
        id: 'dev-user-id',
        email: 'dev@example.com',
        userType: 'globalAdmin'
      })
    );

    // Fake code and state so OktaCallback doesn't throw
    window.location.href = `/okta-callback?code=dev-code&state=dev-state`;
  };

  return (
    <Button
      onClick={redirectToAuth}
      type={'button'}
      size="big"
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
    <Box display="flex" flexDirection="column" height={'calc(100vh - 108px)'}>
      <Box flex={0.5} display="flex" />
      <Box
        flex={0.5}
        display="flex"
        justifyContent="center"
        alignItems="center"
      >
        <Typography variant="h1" textAlign="center">
          Welcome to CyHy Dashboard
        </Typography>
      </Box>
      <Box flex={1} display="flex" justifyContent="center" alignItems="center">
        <LoginButton />
      </Box>
      <Box flex={1} display="flex" />
      <Box justifyContent="center" alignItems="center" pb={5}>
        <CrossfeedWarning />
      </Box>
    </Box>
  );
};
