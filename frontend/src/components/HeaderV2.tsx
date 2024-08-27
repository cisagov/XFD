import React, { FC, useEffect, useState } from 'react';
import { styled } from '@mui/material/styles';
import { NavLink, Link, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  IconButton,
  Drawer,
  ListItem,
  List,
  Box,
  Typography
} from '@mui/material';
import { ChevronLeft, FilterAlt, Menu as MenuIcon } from '@mui/icons-material';
import { NavItem } from './NavItem';
import { useAuthContext } from 'context';
import logo from '../assets/cyhydashboard.svg';
import cisaLogo from '../assets/cisaSeal.svg';
import { UserMenu } from './UserMenu';
import { matchPath } from 'utils/matchPath';
import { display, useTheme } from '@mui/system';
import { useUserLevel } from 'hooks/useUserLevel';

const PREFIX = 'Header';

const classes = {
  inner: `${PREFIX}-inner`,
  menuButton: `${PREFIX}-menuButton`,
  logo: `${PREFIX}-logo`,
  cisaLogo: `${PREFIX}-1cisaLogo`,
  spacing: `${PREFIX}-spacing`,
  activeMobileLink: `${PREFIX}-activeMobileLink`,
  link: `${PREFIX}-link`,
  userLink: `${PREFIX}-userLink`,
  lgNav: `${PREFIX}-lgNav`,
  selectOrg: `${PREFIX}-selectOrg`,
  option: `${PREFIX}-option`
};

const Root = styled('div')(({ theme }) => ({
  [`.${classes.inner}`]: {
    maxWidth: '1440px',
    width: '100%',
    margin: '0 auto'
  },

  [`.${classes.menuButton}`]: {
    marginLeft: theme.spacing(2),
    display: 'flex'
  },
  [`.${classes.cisaLogo}`]: {
    height: 40,
    marginRight: theme.spacing(1)
  },
  [`.${classes.logo}`]: {
    width: 175,
    minWidth: 175,
    padding: theme.spacing(),
    paddingLeft: 0,
    [theme.breakpoints.down('xl')]: {
      display: 'flex'
    }
  },
  [`.${classes.spacing}`]: {
    flexGrow: 1
  },
  [`.${classes.activeMobileLink}`]: {
    fontWeight: 700,
    '&:after': {
      content: "''",
      position: 'absolute',
      top: 0,
      bottom: 0,
      left: 0,
      height: '100%',
      width: 2,
      backgroundColor: theme.palette.primary.main
    }
  },

  [`.${classes.link}`]: {
    position: 'relative',
    color: 'white',
    textDecoration: 'none',
    margin: `0 ${theme.spacing()}px`,
    padding: theme.spacing(),
    borderBottom: '2px solid transparent',
    fontWeight: 600
  },
  [`.${classes.userLink}`]: {
    [theme.breakpoints.down('md')]: {
      display: 'flex'
    },
    [theme.breakpoints.up('lg')]: {
      display: 'flex',
      alignItems: 'center',
      marginLeft: '1rem',
      '& svg': {
        marginRight: theme.spacing()
      },
      border: 'none',
      textDecoration: 'none'
    }
  },
  [`.${classes.lgNav}`]: {
    display: 'flex',
    width: 'max-content',
    [theme.breakpoints.down('sm')]: {
      display: 'flex'
    }
  },

  [`.${classes.selectOrg}`]: {
    border: '1px solid #FFFFFF',
    borderRadius: '5px',
    width: '200px',
    padding: '3px',
    marginLeft: '20px',
    '& svg': {
      color: 'white'
    },
    '& input': {
      color: 'white',
      width: '100%'
    },
    '& input:focus': {
      outlineWidth: 0
    },
    '& fieldset': {
      borderStyle: 'none'
    },
    '& div div': {
      paddingTop: '0 !important'
    },
    '& div div div': {
      marginTop: '-3px !important'
    },
    height: '45px'
  }
}));

const GLOBAL_ADMIN = 3;
const REGIONAL_ADMIN = 2;
const STANDARD_USER = 1;

interface NavItemType {
  title: string | JSX.Element;
  path: string;
  users?: number;
  onClick?: any;
  exact: boolean;
}

interface MenuItemType {
  title: string;
  path: string;
  users?: number;
  onClick?: any;
  exact: boolean;
}

interface HeaderProps {
  isFilterDrawerOpen: boolean;
  setIsFilterDrawerOpen: (isFilterDrawerOpen: boolean) => void;
}

export const HeaderV2: React.FC<HeaderProps> = ({
  isFilterDrawerOpen,
  setIsFilterDrawerOpen
}) => {
  const { pathname } = useLocation();
  const { user, logout } = useAuthContext();
  const theme = useTheme();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  let drawerItems: NavItemType[] = [];
  const toggleDrawer = (newOpen: boolean) => () => {
    setDrawerOpen(newOpen);
  };

  const { userLevel, formattedUserType } = useUserLevel();

  const navItems: NavItemType[] = [
    {
      title: 'Overview',
      path: '/',
      users: STANDARD_USER,
      exact: true,
      onClick: toggleDrawer(false)
    },
    {
      title: 'Inventory',
      path: '/inventory',
      users: STANDARD_USER,
      exact: false,
      onClick: toggleDrawer(false)
    }
  ].filter(({ users }) => users <= userLevel);

  const userMenuItems: MenuItemType[] = [
    {
      title: 'Admin Tools',
      path: '/admin-tools',
      users: GLOBAL_ADMIN,
      exact: true
    },
    {
      title: 'User Registration',
      path: '/region-admin-dashboard',
      users: REGIONAL_ADMIN,
      exact: true
    },
    {
      title: 'Manage Organizations',
      path: '/organizations',
      users: REGIONAL_ADMIN,
      exact: true
    },
    {
      title: 'Manage Users',
      path: '/users',
      users: REGIONAL_ADMIN,
      exact: true
    },
    {
      title: 'My Settings',
      path: '/settings',
      users: STANDARD_USER,
      exact: true
    },
    {
      title: 'Logout',
      path: '/settings',
      users: STANDARD_USER,
      onClick: logout,
      exact: true
    }
  ];

  // const orgPageMatch = useRouteMatch('/organizations/:id');

  const desktopNavItems: JSX.Element[] = navItems.map((item) => (
    <NavItem key={item.title.toString()} {...item} />
  ));

  const handleResize = () => {
    if (window.innerWidth < 1330) {
      setIsMobile(true);
    } else {
      setIsMobile(false);
    }
  };

  useEffect(() => {
    window.addEventListener('resize', handleResize);
  });

  if (isMobile && userMenuItems) {
    userMenuItems.forEach((item) => {
      if (item.title !== 'Logout') {
        item.onClick = toggleDrawer(false);
      }
    });
    drawerItems = [...navItems, ...userMenuItems];
  }

  return (
    <Root>
      <AppBar position="static" elevation={0}>
        <Box
          maxWidth="1440px"
          display="flex"
          width="100%"
          height="100%"
          margin="0 auto"
          flexWrap="wrap"
          alignItems="center"
        >
          <Toolbar sx={{ width: '100%', display: 'flex' }}>
            <Box
              display="flex"
              flexDirection="row"
              width="100%"
              alignItems="center"
            >
              {matchPath(['/', '/inventory'], pathname) && user ? (
                <FilterDrawerButton
                  open={isFilterDrawerOpen}
                  setOpen={setIsFilterDrawerOpen}
                />
              ) : (
                <></>
              )}
              <img
                src={cisaLogo}
                style={{
                  height: 40,
                  marginRight: theme.spacing(1)
                }}
                alt="Cybersecurity and Infrastructure Security Agency Logo"
              />
              <Link
                to="/"
                style={{ width: 'min-content', height: 'min-content' }}
              >
                <img
                  src={logo}
                  style={{
                    width: 175,
                    maxWidth: 175,
                    padding: theme.spacing(),
                    paddingLeft: 0,
                    [theme.breakpoints.down('xl')]: {
                      display: 'flex'
                    }
                  }}
                  alt="CyHy Dashboard Icon Navigate Home"
                />
              </Link>
              {!isMobile && (
                <Box
                  display="flex"
                  width="max-content"
                  sx={{
                    [theme.breakpoints.down('sm')]: {
                      display: 'flex'
                    }
                  }}
                >
                  {desktopNavItems.slice()}
                </Box>
              )}
            </Box>
            <Box
              textTransform="uppercase"
              display="flex"
              width="auto"
              minWidth="max-content"
            >
              {user && userLevel > 1 ? (
                <Typography>{formattedUserType}</Typography>
              ) : (
                <></>
              )}
            </Box>
            <Box
              display="flex"
              flexDirection="row"
              width="100%"
              justifyContent="end"
            >
              {userLevel > 0 && (
                <>{!isMobile && <UserMenu userMenuItems={userMenuItems} />}</>
              )}
              {user && isMobile && (
                <IconButton
                  edge="start"
                  style={{
                    marginLeft: theme.spacing(2),
                    display: 'flex'
                  }}
                  aria-label="toggle mobile menu"
                  color="inherit"
                  onClick={toggleDrawer(true)}
                >
                  <MenuIcon />
                </IconButton>
              )}
            </Box>
          </Toolbar>
        </Box>
      </AppBar>
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={toggleDrawer(false)}
        data-testid="mobilenav"
        PaperProps={{
          sx: {
            backgroundColor: 'primary.main',
            color: 'white'
          }
        }}
      >
        <List sx={{ p: 2 }}>
          {drawerItems.map(({ title, path }) => (
            <React.Fragment key={title.toString()}>
              {path && (
                <ListItem
                  sx={{ color: 'white' }}
                  exact
                  component={NavLink}
                  to={path}
                >
                  {title}
                </ListItem>
              )}
            </React.Fragment>
          ))}
        </List>
      </Drawer>
    </Root>
  );
};

interface FilterDrawerButtonProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const FilterDrawerButton: FC<FilterDrawerButtonProps> = ({ open, setOpen }) => {
  return (
    <IconButton
      onClick={() => setOpen(!open)}
      aria-label={open ? 'Close filter drawer' : 'Open filter drawer'}
    >
      {open ? (
        <ChevronLeft style={{ color: 'white' }} />
      ) : (
        <FilterAlt style={{ color: 'white' }} />
      )}
    </IconButton>
  );
};
