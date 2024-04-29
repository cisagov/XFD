import React from 'react';
import { Divider, useScrollTrigger } from '@mui/material';
import Box from '@mui/material/Box';
import Fab from '@mui/material/Fab';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import NavigationIcon from '@mui/icons-material/Navigation';
import Zoom from '@mui/material/Zoom';
import { HashLink } from 'react-router-hash-link';

interface Props {
  categories: Category[];
}

export interface Category {
  name: string;
}
export const FloatingNav: React.FC<Props> = ({ categories }) => {
  const trigger = useScrollTrigger({
    threshold: 100
  });
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <>
      <Zoom in={trigger}>
        <Box
          role="presentation"
          sx={{
            position: 'fixed',
            bottom: 80,
            right: 32,
            zIndex: 1
          }}
        >
          <Fab
            onClick={handleClick}
            color="primary"
            size="small"
            aria-label="Scroll back to top"
            style={{ outline: 'none' }}
          >
            <NavigationIcon fontSize="medium" />
          </Fab>
        </Box>
      </Zoom>
      <Menu
        id="basic-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'top',
          horizontal: 'left'
        }}
        transformOrigin={{
          vertical: 'bottom',
          horizontal: 'right'
        }}
        MenuListProps={{
          'aria-labelledby': 'basic-button'
        }}
      >
        {categories.map((category, index) => (
          <div key={index}>
            <HashLink
              style={{
                textDecoration: 'none',
                color: 'black',
                outline: 'none'
              }}
              to={`#${category.name}`}
            >
              <MenuItem onClick={handleClose}>{category.name}</MenuItem>
            </HashLink>
            <Divider />
          </div>
        ))}
      </Menu>
    </>
  );
};
