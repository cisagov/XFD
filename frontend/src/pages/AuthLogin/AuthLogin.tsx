import React, { useEffect } from 'react';
import { useAuthContext } from 'context';
import { Button } from '@trussworks/react-uswds';
import { Alert, AlertTitle, Box, Grid, Typography } from '@mui/material';
import { CrossfeedWarning } from 'components/WarningBanner';
import { initialNotificationValues, MaintenanceNotification } from 'types';

const LoginButton = () => {
  // TODO: Capture default values here once determined
  const domain = process.env.REACT_APP_COGNITO_DOMAIN || 'default_value';
  const clientId = process.env.REACT_APP_COGNITO_CLIENT_ID || 'default_value';
  const callbackUrl =
    process.env.REACT_APP_COGNITO_CALLBACK_URL || 'default_value';
  const encodedCallbackUrl = encodeURIComponent(callbackUrl);

  const redirectToAuth = () => {
    // Adjust this callback URL once determined
    window.location.href = `https://${domain}/oauth2/authorize?identity_provider=Okta&redirect_uri=${encodedCallbackUrl}&response_type=CODE&client_id=${clientId}&scope=email openid profile`;
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
      const activeRow = rows.find((row: MaintenanceNotification) => {
        return row.status === 'active';
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
      notification?.maintenanceType === 'major' &&
      notification?.status === 'active';
    const titleText = isLoginUnavailable
      ? 'Crossfeed Major Maintenance: Login Not Available'
      : 'Crossfeed Maintenance Notification';

    return <AlertTitle>{titleText}</AlertTitle>;
  };

  const platformNotification = (
    <Grid item xs={12}>
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
      height="100vh"
    >
      {notification?.status === 'active' && platformNotification}
      <Typography variant="h3" textAlign="center">
        Welcome to Crossfeed
      </Typography>
      <Box pt={3} mb={3} display="flex" justifyContent="center">
        <LoginButton />
      </Box>
      <CrossfeedWarning />
    </Box>
  );
};
