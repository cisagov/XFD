import React from 'react';
import { Box, Typography } from '@mui/material';

export const RSCLogin: React.FC = () => {
  // This is a placeholder for the Ready Set Cyber login page.
  // The original legacy code utilized a registration and login system prior to the SSO Okta solution we now use.
  // That system triggered vulnerabilities in the 08/24 ST&E Report.
  // It was removed and replaced with this placeholder until an Okta/Login.gov integration is implemented for Ready Set Cyber in a future sprint.
  // RSCRegisterForm.tsx and RSCAuthLoginCreate.tsx were also deleted.
  // [CRASM-736](https://maestro.dhs.gov/jira/browse/CRASM-736)
  return (
    <Box>
      <Typography variant="h1">Ready Set Cyber</Typography>
    </Box>
  );
};
