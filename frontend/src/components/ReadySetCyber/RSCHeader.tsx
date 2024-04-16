import React from 'react';
import { AppBar } from '@mui/material';
import { Toolbar } from '@mui/material';
import { Typography } from '@mui/material';
import { useHistory } from 'react-router-dom';
import { ScrollTop } from './ScrollTop';

export const RSCHeader: React.FC = () => {
  const history = useHistory();
  const handleClick = () => {
    history.push('/readysetcyber');
  };
  return (
    <>
      <AppBar position="fixed">
        <Toolbar>
          <Typography variant="h6" onClick={handleClick}>
            Ready Set Cyber
          </Typography>
        </Toolbar>
      </AppBar>
      <Toolbar />{' '}
      {/* Placeholder to prevent content from being hidden under the AppBar */}
      <ScrollTop />
    </>
  );
};
