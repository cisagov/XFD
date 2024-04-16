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
    <div>
      <Box
        sx={{
          width: '100%',
          maxWidth: 360,
          bgcolor: 'background.paper',
          position: 'sticky'
        }}
      >
        <List>
          <ListItem>Welcome, {user?.fullName ?? 'Guest'}</ListItem>
          <Divider component="li" />
          <ListItemButton>Take Questionnaire Again</ListItemButton>
          <Divider component="li" />
          <ListItemButton onClick={logout}>Logout</ListItemButton>
        </List>
      </Box>
    </div>
  );
};
