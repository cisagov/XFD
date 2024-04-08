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
import AccountCircle from '@mui/icons-material/AccountCircle';
import MenuIcon from '@mui/icons-material/Menu';
import RSCLogo from 'components/ReadySetCyber/Assets/ReadySetCyberLogo.png';

export const RSCHeader: React.FC = () => {
  const history = useHistory();
  const handleClick = () => {
    history.push('/readysetcyber');
  };
  const { logout, user } = useAuthContext();

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(
    null
  );

  const handleOpenNavMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElNav(event.currentTarget);
  };

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleCloseNavMenu = () => {
    setAnchorElNav(null);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" sx={{ bgcolor: 'white' }}>
        <Container maxWidth="xl">
          <Toolbar disableGutters>
            <Tooltip title="Go to Ready Set Cyber" arrow>
              <IconButton
                onClick={handleClick}
                sx={{ display: { xs: 'none', md: 'flex' } }}
              >
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
              sx={{
                flexGrow: 1,
                color: '#07648D',
                display: { xs: 'none', md: 'flex' }
              }}
            >
              Dashboard
            </Typography>
            <Box sx={{ flexGrow: 1, display: { xs: 'flex', md: 'none' } }}>
              <IconButton
                size="large"
                aria-label="account of current user"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                color="primary"
                onClick={handleOpenNavMenu}
              >
                <MenuIcon />
              </IconButton>
              <Menu
                id="menu-appbar"
                anchorEl={anchorElNav}
                anchorOrigin={{
                  vertical: 'top',
                  horizontal: 'right'
                }}
                keepMounted
                transformOrigin={{
                  vertical: 'top',
                  horizontal: 'right'
                }}
                open={Boolean(anchorElNav)}
                onClose={handleCloseNavMenu}
              >
                <MenuItem>Dashboard</MenuItem>
              </Menu>
            </Box>
            <Tooltip title="Go to Ready Set Cyber" arrow>
              <IconButton
                onClick={handleClick}
                sx={{ display: { xs: 'flex', md: 'none' } }}
              >
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
