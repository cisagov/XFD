import React from 'react';
import { useAuthContext } from 'context';
import { Button, Typography, Box, Paper } from '@mui/material';

const Settings: React.FC = () => {
  const { logout, user } = useAuthContext();

  return (
    <Box
      sx={{
        padding: 3,
        maxWidth: 800,
        margin: '0 auto'
      }}
    >
      <Paper
        elevation={1}
        sx={{
          padding: 3,
          borderRadius: 2
        }}
      >
        <Typography variant="h4" component="h1" gutterBottom>
          My Account
        </Typography>

        <Typography variant="h6" component="h2" sx={{ mb: 2 }}>
          Name: {user && user.full_name}
        </Typography>

        <Typography variant="h6" component="h2" sx={{ mb: 2 }}>
          Email: {user && user.email}
        </Typography>

        <Typography variant="h6" component="h2" sx={{ mb: 2 }}>
          Member of:{' '}
          {user &&
            (user.roles || [])
              .filter((role) => role.approved)
              .map((role) => role.organization.name)
              .join(', ')}
        </Typography>

        <Typography variant="h6" component="h2" sx={{ mb: 3 }}>
          Region: {user && user.region_id ? user.region_id : 'None'}
        </Typography>

        <Button
          variant="contained"
          color="primary"
          onClick={logout}
          size="large"
        >
          Logout
        </Button>
      </Paper>
    </Box>
  );
};

export default Settings;
