import React from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Divider from '@mui/material/Divider';

export const RSCDefaultSideNav: React.FC = () => {
  const handleRSCredirect = () => {
    window.open(
      'https://cisaexdev.servicenowservices.com/rsc?id=rsc_welcome',
      '_blank'
    );
  };

  return (
    <div>
      <Box sx={{ width: '100%', maxWidth: 360, bgcolor: 'background.paper' }}>
        <List>
          <ListItem>Welcome User</ListItem>
          <Divider component="li" />
          <ListItem onClick={handleRSCredirect} style={{ cursor: 'pointer' }}>
            Take Questionnaire Again
          </ListItem>
          <Divider component="li" />
          <ListItem>Logout</ListItem>
        </List>
      </Box>
    </div>
  );
};
