import React from 'react';
import { Box, Grid } from '@mui/material';
import { useAuthContext } from 'context';
import useFirstLoginPopup from 'hooks/useFirstLoginPopup';
import InfoLabel from 'components/Dashboard/InfoLabel';
import FirstLoginPopup from 'components/Dialog/FirstLoginPopup';
import infoIconContent from 'pages/VulnerabilityScanDash/infoIconContent.json';

const tooltipContentJson = infoIconContent.infoIconContent;

const PageSection = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuthContext();
  const { show: showFirstLoginPopup, close: handleCloseFirstLoginPopup } =
    useFirstLoginPopup(user ?? null);
  return (
    <Box
      sx={{
        maxWidth: '1152px',
        margin: 'auto',
        px: { xs: 0, sm: 0.5, md: 1, lg: 1, xl: 0 },
        pb: 6,
        minHeight: '100vh'
      }}
    >
      <Grid container mb={0}>
        <Grid size={{ xs: 12 }} sx={{ mt: 4 }}>
          <InfoLabel
            label="Vulnerability Scanning Dashboard"
            typographyVariant="h1"
            viewDetails
            tooltipContentJson={tooltipContentJson}
          />
        </Grid>
      </Grid>
      <FirstLoginPopup
        showFirstLoginPopup={showFirstLoginPopup}
        handleCloseFirstLoginPopup={handleCloseFirstLoginPopup}
      />
      {children}
    </Box>
  );
};

export default PageSection;
