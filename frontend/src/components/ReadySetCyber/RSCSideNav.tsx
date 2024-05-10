import React from 'react';
import { useAuthContext } from 'context';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Divider from '@mui/material/Divider';
import { RSCNavItem } from './RSCNavItem';
import { ListItemButton } from '@mui/material';

interface Props {
  categories: Category[];
}

export interface Category {
  name: string;
}

export const RSCSideNav: React.FC<Props> = ({ categories }) => {
  const { user, logout } = useAuthContext();

  return (
    <Box>
      <Box
        sx={{
          width: '100%',
          maxWidth: 360,
          bgcolor: 'background.paper'
        }}
      >
        <List>
          <ListItem>Welcome, {user?.fullName ?? 'Guest'}</ListItem>
          <Divider component="li" />
          {categories.map((category, index) => (
            <RSCNavItem key={index} name={category.name} />
          ))}
          <ListItemButton>Take Questionnaire Again</ListItemButton>
          <Divider component="li" />
          <ListItemButton onClick={logout}>Logout</ListItemButton>
        </List>
      </Box>
    </Box>
  );
};
