import React from 'react';
import { Alert, AlertTitle, Typography, Link } from '@mui/material';

interface CustomAlertProps {
  headerMsg?: string;
  bodyMsg?: React.ReactNode;
  isActive?: boolean;
}

const CustomAlert: React.FC<CustomAlertProps> = ({
  headerMsg = 'No Data Found',
  bodyMsg = null,
  isActive = 'false'
}) => {
  const defaultMsg = (
    <>
      No data was found for this organization. Contact CyHy team through the
      Support menu.
    </>
  );
  if (isActive) {
    return (
      <Alert severity="info" sx={{ width: '100%' }}>
        <AlertTitle
          variant="largeBody"
          color="primary.darker"
          sx={{ fontWeight: 700 }}
        >
          {headerMsg}
        </AlertTitle>
        <Typography variant="body1" color="primary.darker" fontWeight={600}>
          {bodyMsg || defaultMsg}
        </Typography>
      </Alert>
    );
  }
  return null;
};

export default CustomAlert;
