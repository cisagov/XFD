import React from 'react';
import { AppBar } from '@mui/material';
import { Toolbar } from '@mui/material';
import { Typography } from '@mui/material';

export const RSCHeader: React.FC = () => {
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6">Ready Set Cyber</Typography>
      </Toolbar>
    </AppBar>
  );
};
// Path: frontend/src/components/ReadySetCyber/ReadySetCyber.tsx
