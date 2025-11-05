import React from 'react';
import { Box, IconButton, Modal, Typography } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

type FirstLoginPopupProps = {
  showFirstLoginPopup: boolean;
  handleCloseFirstLoginPopup: () => void | Promise<void>;
};

const firstLoginPopup: React.FC<FirstLoginPopupProps> = ({
  showFirstLoginPopup,
  handleCloseFirstLoginPopup
}) => {
  return (
    <Modal open={!!showFirstLoginPopup} onClose={handleCloseFirstLoginPopup}>
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          backgroundColor: 'rgba(0,0,0,0.4)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 2000
        }}
      >
        <Box
          sx={{
            backgroundColor: '#fff',
            borderRadius: 2,
            boxShadow: 3,
            p: 4,
            maxWidth: 570,
            maxHeight: 395,
            minWidth: 570,
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-start',
            pb: '24px'
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography
              variant="h2"
              gutterBottom
              sx={{ textAlign: 'left', mb: 0, mt: -2, flexGrow: 1 }}
            >
              Welcome to the CyHy Dashboard!
            </Typography>
            <IconButton
              aria-label="close"
              onClick={handleCloseFirstLoginPopup}
              sx={{
                ml: 1,
                mt: -2,
                mr: -1,
                color: (theme) => theme.palette.neutrals.black
              }}
              size="large"
            >
              <CloseIcon />
            </IconButton>
          </Box>

          <Box
            sx={{
              width: '570px',
              height: '4pt',
              backgroundColor: (theme) => theme.palette.primary.dark,
              mt: '-10px',
              mb: '10px',
              ml: '-32px'
            }}
          />
          <Box sx={{ flex: 1, overflowY: 'auto', width: '100%', mt: '10px' }}>
            <Typography variant="body1" sx={{ textAlign: 'left', mb: 2 }}>
              Here you can monitor your organization&apos;s public-facing attack
              surface by reviewing key vulnerabilities, tracking affected assets
              and services, and exploring detailed data through the Findings
              Library.
            </Typography>
            <Typography variant="body1" sx={{ textAlign: 'left', mb: 2 }}>
              Need help as you explore? Look for information icons throughout
              the dashboard for quick tips. You can also visit the Learning
              Center and Support menus for additional guidance and resources.
            </Typography>
            <Typography variant="body1" sx={{ textAlign: 'left', mb: 2 }}>
              You are now entering the{' '}
              <strong>Vulnerability Scanning Dashboard</strong> which provides
              near real time access to scan data along with interactive
              visualizations. New dashboards and features will be added over
              time - keep an eye out for updates.
            </Typography>
            <Box sx={{ textAlign: 'left' }}>
              <Typography variant="globalNav">
                Ready to dive in? Let&apos;s get started!
              </Typography>
            </Box>
          </Box>
        </Box>
      </Box>
    </Modal>
  );
};
export default firstLoginPopup;
