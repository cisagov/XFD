import React from 'react';
import { useAuthContext } from 'context';
import {
  useUserLevel,
  GLOBAL_ADMIN,
  REGIONAL_ADMIN,
  STANDARD_USER
} from 'hooks/useUserLevel';
import { AppBar, Box, IconButton, Toolbar, Typography } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import cisaLogo from 'assets/cisaSeal.svg';
import { NavMenuButton } from './NavMenuButton';
import { NavMenuDrawer } from './NavMenuDrawer';

interface MenuItemType {
  menuItemTitle: string;
  path: string;
  users?: number;
  onClick?: any;
}

export const Header: React.FC = () => {
  const { logout } = useAuthContext();
  const { userLevel } = useUserLevel();
  const [openDrawer, setOpenDrawer] = React.useState(false);
  const toggleDrawer = (newOpen: boolean) => () => {
    setOpenDrawer(newOpen);
  };
  const adminHubMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Admin Tools',
      path: '/admin-tools',
      users: GLOBAL_ADMIN
    },
    {
      menuItemTitle: 'User Registration',
      path: '/region-admin-dashboard',
      users: REGIONAL_ADMIN
    },
    {
      menuItemTitle: 'Manage Organizations',
      path: '/organizations',
      users: REGIONAL_ADMIN
    },
    {
      menuItemTitle: 'Manage Users',
      path: '/users',
      users: REGIONAL_ADMIN
    }
  ].filter(({ users }) => users <= userLevel);

  const userMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Account Settings',
      path: '/settings',
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Logout',
      path: '/settings',
      users: STANDARD_USER,
      onClick: logout
    }
  ].filter(({ users }) => users <= userLevel);

  // TODO: Add path for below menu items
  const scanningResults: MenuItemType[] = [
    {
      menuItemTitle: 'Overview',
      path: '/',
      users: STANDARD_USER
    },
    {
      menuItemTitle: 'Vulnerability Scanning',
      path: '/VSDashboard',
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const supportMenuItems: MenuItemType[] = [
    // {
    //   menuItemTitle: 'Report Bug',
    //   path: '#',
    //   users: STANDARD_USER
    // },
    {
      menuItemTitle: 'Send Feedback',
      path: 'mailto:vulnerability@mail.cisa.dhs.gov',
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const learningCenterMenuItems: MenuItemType[] = [
    // {
    //   menuItemTitle: 'Glossary',
    //   path: '#',
    //   users: STANDARD_USER
    // },
    // {
    //   menuItemTitle: 'FAQ',
    //   path: '#',
    //   users: STANDARD_USER
    // },
    {
      menuItemTitle: 'CISA Resources',
      path: 'https://www.cisa.gov',
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const inventoryMenuItems: MenuItemType[] = [
    {
      menuItemTitle: 'Inventory',
      path: '/inventory',
      users: STANDARD_USER
    }
  ].filter(({ users }) => users <= userLevel);

  const allMenuItems: { [section: string]: MenuItemType[] }[] = [
    { 'Scanning Results': scanningResults },
    { Inventory: inventoryMenuItems },
    { 'Learning Center': learningCenterMenuItems },
    { Support: supportMenuItems },
    userLevel > 1 ? { 'Admin Hub': adminHubMenuItems } : {},
    { 'My Account': userMenuItems }
  ];

  const headerLogo = (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'left',
        width: '100%',
        transition: 'margin-left 0.3s ease-in-out'
      }}
    >
      <Box component="img" src={cisaLogo} sx={{ height: 60 }} alt="C Logo" />
      <Typography
        variant="h1"
        sx={{ fontSize: '22px', color: 'primary.darker' }}
      >
        CyHy Dashboard
      </Typography>
    </Box>
  );

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        backgroundColor: 'neutrals.white',
        borderBottom: '0.5px solid',
        borderColor: 'neutrals.light',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '84px'
      }}
    >
      <Toolbar disableGutters sx={{ maxWidth: '1152px', width: '100%', p: 0 }}>
        {headerLogo}
        {userLevel > 0 && (
          <>
            {allMenuItems.map((sectionObj, index) => {
              const [title, menuItems] = Object.entries(sectionObj)[0] || [];
              if (!title || !menuItems) {
                return null;
              } else if (title === 'Learning Center') {
                return (
                  <Box key={title + index} sx={{ mr: { xs: 0, xl: 4 } }}>
                    <NavMenuButton title={title} menuItems={menuItems} />
                  </Box>
                );
              }
              return (
                <NavMenuButton
                  key={title + index}
                  title={title}
                  menuItems={menuItems}
                />
              );
            })}
            <IconButton
              sx={{
                display: { xs: 'flex', lg: 'none' },
                color: 'primary.dark'
              }}
              aria-label="Open mobile menu"
              aria-haspopup="true"
              aria-controls={openDrawer ? 'mobile-menu' : undefined}
              aria-expanded={openDrawer ? 'true' : undefined}
              onClick={toggleDrawer(!openDrawer)}
            >
              <MenuIcon />
            </IconButton>
            <NavMenuDrawer
              openDrawer={openDrawer}
              toggleDrawer={toggleDrawer}
              menuItems={allMenuItems}
            />
          </>
        )}
      </Toolbar>
    </AppBar>
  );
};
