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
import RSCLogo from 'components/ReadySetCyber/assets/ReadySetCyberLogo.png';

export const RSCHeader: React.FC = () => {
  const history = useHistory();
  const handleNavHome = () => {
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
    <>
      <AppBar position="relative" sx={{ bgcolor: 'white' }}>
        <Container maxWidth="xl">
          <Toolbar disableGutters>
            <Tooltip title="Go to Ready Set Cyber" arrow>
              <IconButton
                onClick={handleNavHome}
                sx={{ display: { xs: 'none', md: 'flex' }, mr: 1 }}
                style={{ backgroundColor: 'white' }}
                disableFocusRipple
              >
                <img
                  src={RSCLogo}
                  alt="Ready Set Cyber Logo"
                  style={{
                    width: '4em',
                    height: '2em'
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
                display: { xs: 'none', md: 'flex' },
                mr: 2
              }}
            >
              Dashboard
            </Typography>
            <Box sx={{ flexGrow: 1, display: { xs: 'flex', md: 'none' } }}>
              <Tooltip title="Go to Ready Set Cyber" arrow>
                <IconButton
                  onClick={handleNavHome}
                  sx={{ display: { xs: 'flex', md: 'none' }, mr: 0 }}
                  style={{ backgroundColor: 'white' }}
                >
                  <img
                    src={RSCLogo}
                    alt="Ready Set Cyber Logo"
                    style={{
                      width: '4em',
                      height: '2em'
                    }}
                  />
                </IconButton>
              </Tooltip>
            </Box>
            {user && (
              <>
                <IconButton
                  size="large"
                  aria-label="nav menu"
                  aria-controls="menu-navbar"
                  aria-haspopup="true"
                  color="primary"
                  onClick={handleOpenNavMenu}
                  style={{ outline: 'none' }}
                  sx={{ display: { xs: 'block', md: 'none' } }}
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
                  sx={{ display: { xs: 'block', md: 'none' } }}
                >
                  <MenuItem style={{ outline: 'none' }}>
                    {' '}
                    Welcome, {user.fullName}{' '}
                  </MenuItem>
                  <MenuItem style={{ outline: 'none' }} onClick={handleNavHome}>
                    Dashboard
                  </MenuItem>
                  <MenuItem style={{ outline: 'none' }}>
                    {' '}
                    Take Questionnaire Again{' '}
                  </MenuItem>
                  <MenuItem style={{ outline: 'none' }} onClick={logout}>
                    Logout
                  </MenuItem>
                </Menu>
              </>
            )}
            {user && (
              <Box sx={{ flexGrow: 0, display: { xs: 'none', md: 'flex' } }}>
                <Tooltip title="Open Menu" arrow>
                  <IconButton
                    sx={{ p: 0 }}
                    size="large"
                    aria-label="account of current user"
                    aria-controls="menu-appbar"
                    aria-haspopup="true"
                    color="primary"
                    onClick={handleMenu}
                    style={{ outline: 'none' }}
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
                  <MenuItem style={{ outline: 'none' }} onClick={logout}>
                    Logout
                  </MenuItem>
                </Menu>
              </Box>
            )}
          </Toolbar>
        </Container>
      </AppBar>
    </>
  );
};
