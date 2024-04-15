import React from 'react';
import { useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Divider from '@mui/material/Divider';

export const RSCDefaultSideNav: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <div>
      <Box sx={{ width: '100%', maxWidth: 360, bgcolor: 'background.paper' }}>
        <List>
          <ListItem>Welcome User</ListItem>
          <Divider component="li" />
          <ListItem>Take Questionnaire Again</ListItem>
          <Divider component="li" />
          <ListItem>Logout</ListItem>
        </List>
      </Box>
    </div>
  );
};
