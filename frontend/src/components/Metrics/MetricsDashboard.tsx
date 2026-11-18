import React from 'react';

// Material-UI Components
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';

// Assets
import MatomoLogo from '@/assets/matomo-logo.png';

// Components
import ScansWidget from './Widgets/ScansWidget';

// Constants
import { ROUTES } from '@/constants/routes';

// Context
import { useAuthContext } from '@/context/AuthContext';

const MetricsDashboard: React.FC = () => {
  const { user } = useAuthContext();

  return (
    <Box p={2}>
      {user?.user_type === 'globalAdmin' && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
          <Button
            variant="contained"
            sx={{
              backgroundColor: (theme) => theme.palette.primary.dark,
              color: '#fff',
              '&:hover': {
                backgroundColor: (theme) => theme.palette.primary.darker
              },
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}
            onClick={() =>
              window.open(ROUTES.MATOMO, '_blank', 'noopener,noreferrer')
            }
            aria-label="Open Matomo Dashboard"
          >
            <img
              src={MatomoLogo}
              alt="Matomo Logo"
              style={{ height: 24, width: 24 }}
            />
            Matomo
          </Button>
        </Box>
      )}
      <ScansWidget />
    </Box>
  );
};

export default MetricsDashboard;
