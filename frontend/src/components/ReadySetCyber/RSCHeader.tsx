import React from 'react';
import { AppBar } from '@mui/material';
import { Toolbar } from '@mui/material';
import { Typography } from '@mui/material';
import { useHistory } from 'react-router-dom';

export const RSCHeader: React.FC = () => {
  const history = useHistory();
  const handleClick = () => {
    history.push('/readysetcyber');
  };
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" onClick={handleClick}>
          Ready Set Cyber
        </Typography>
      </Toolbar>
    </AppBar>
  );
};
