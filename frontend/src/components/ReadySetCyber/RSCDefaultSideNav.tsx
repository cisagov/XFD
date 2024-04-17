import React from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Divider from '@mui/material/Divider';
import { useAuthContext } from 'context';
import { ListItemButton } from '@mui/material';

export const RSCDefaultSideNav: React.FC = () => {
  const { user, logout } = useAuthContext();

  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: 360,
        bgcolor: 'background.paper',
        position: 'fixed'
      }}
    >
      <List>
        <ListItem>Welcome, {user?.fullName ?? 'Guest'}</ListItem>
        <Divider component="li" />
        <ListItemButton style={{ outline: 'none' }}>
          Take Questionnaire Again
        </ListItemButton>
        <Divider component="li" />
        <ListItemButton style={{ outline: 'none' }} onClick={logout}>
          Logout
        </ListItemButton>
      </List>
    </Box>
  );
};
