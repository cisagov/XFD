import React from 'react';
import { useHistory } from 'react-router-dom';
import { useAuthContext } from 'context';
import {
  AppBar,
  Toolbar,
  Container,
  Box,
  Typography,
  IconButton,
  Menu,
  MenuItem,
  Tooltip
} from '@mui/material';
import { AccountCircle } from '@mui/icons-material';
import RSCLogo from 'components/ReadySetCyber/Assets/ReadySetCyberLogo.png';

export const RSCHeader: React.FC = () => {
  const history = useHistory();
  const handleClick = () => {
    history.push('/readysetcyber');
  };
  const { logout, user } = useAuthContext();

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" sx={{ bgcolor: 'white' }}>
        <Container maxWidth="xl">
          <Toolbar>
            <Tooltip title="Go to Ready Set Cyber" arrow>
              <IconButton onClick={handleClick}>
                <img
                  src={RSCLogo}
                  alt="Ready Set Cyber Logo"
                  style={{
                    width: '100px',
                    height: '50px',
                    marginRight: '10px'
                  }}
                />
              </IconButton>
            </Tooltip>
            <Typography
              variant="h6"
              component="div"
              sx={{ flexGrow: 1, color: '#07648D' }}
            >
              Dashboard
            </Typography>
            {user && (
              <div>
                <Tooltip title="Open Menu" arrow>
                  <IconButton
                    size="large"
                    aria-label="account of current user"
                    aria-controls="menu-appbar"
                    aria-haspopup="true"
                    color="primary"
                    onClick={handleMenu}
                  >
                    <AccountCircle />
                  </IconButton>
                </Tooltip>
                <Menu
                  sx={{ marginTop: '40px' }}
                  id="menu-appbar"
                  anchorEl={anchorEl}
                  anchorOrigin={{
                    vertical: 'top',
                    horizontal: 'right'
                  }}
                  keepMounted
                  transformOrigin={{
                    vertical: 'top',
                    horizontal: 'right'
                  }}
                  open={Boolean(anchorEl)}
                  onClose={handleClose}
                >
                  <MenuItem onClick={logout}>Logout</MenuItem>
                  <MenuItem onClick={handleClose}>Profile</MenuItem>
                </Menu>
              </div>
            )}
          </Toolbar>
        </Container>
      </AppBar>
    </Box>
  );
};
