import React from 'react';
import { Box, Button, Card, CardContent, Typography } from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { useAuthContext } from 'context';

const InvitePendingCard: React.FC = ({}) => {
  const { logout, user } = useAuthContext();
  const theme = useTheme();
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: alpha(theme.palette.neutrals.main, 0.7),
        zIndex: 1300
      }}
    >
      <Card style={{ maxWidth: 400, textAlign: 'center' }}>
        <CardContent>
          <CheckCircleOutlineIcon
            sx={{
              fontSize: 48,
              color: (theme) => theme.palette.primary.dark,
              mb: 1
            }}
          />
          <Typography variant="body1" sx={{ mb: 2 }}>
            Request sent! We will notify you by email once your account is
            approved.
          </Typography>
          <Button
            variant="contained"
            sx={{
              backgroundColor: (theme) => theme.palette.primary.dark,
              color: '#fff',
              '&:hover': {
                backgroundColor: (theme) => theme.palette.primary.main
              }
            }}
            onClick={logout}
          >
            Logout
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
};

export default InvitePendingCard;
