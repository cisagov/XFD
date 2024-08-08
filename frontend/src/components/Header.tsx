import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { styled } from '@mui/material/styles';
import { NavLink, Link, useHistory, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  IconButton,
  Drawer,
  ListItem,
  List,
  TextField
} from '@mui/material';
import { Menu as MenuIcon } from '@mui/icons-material';
import { NavItem } from './NavItem';
import { useRouteMatch } from 'react-router-dom';
import { useAuthContext } from 'context';
import logo from '../assets/cyhydashboard.svg';
import cisaLogo from '../assets/cisaSeal.svg';
import { Autocomplete } from '@mui/material';
import { Organization, OrganizationTag } from 'types';
import { UserMenu } from './UserMenu';
import { SideDrawerWithSearch } from './SideDrawer';

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
  mobileNav: `${PREFIX}-mobileNav`,
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
    [theme.breakpoints.down('sm')]: {
      display: 'flex'
    }
  },

  [`.${classes.mobileNav}`]: {
    padding: `${theme.spacing(2)} ${theme.spacing()}px`
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

export const Header: React.FC = () => {
  const history = useHistory();
  const { pathname } = useLocation();
  const {
    currentOrganization,
    setOrganization,
    showAllOrganizations,
    setShowAllOrganizations,
    setShowMaps,
    user,
    logout,
    apiGet
  } = useAuthContext();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [tags, setTags] = useState<OrganizationTag[]>([]);

  let drawerItems: NavItemType[] = [];
  const toggleDrawer = (newOpen: boolean) => () => {
    setDrawerOpen(newOpen);
  };

  let userLevel = 0;
  if (user && user.isRegistered) {
    if (user.userType === 'standard') {
      userLevel = STANDARD_USER;
    } else if (user.userType === 'globalAdmin') {
      userLevel = GLOBAL_ADMIN;
    } else if (
      user.userType === 'regionalAdmin' ||
      user.userType === 'globalView'
    ) {
      userLevel = REGIONAL_ADMIN;
    }
  }

  const fetchOrganizations = useCallback(async () => {
    try {
      const rows = await apiGet<Organization[]>('/v2/organizations/');
      let tags: OrganizationTag[] = [];
      if (userLevel === GLOBAL_ADMIN) {
        tags = await apiGet<OrganizationTag[]>('/organizations/tags');
        await setTags(tags as OrganizationTag[]);
      }
      await setOrganizations(rows);
    } catch (e) {
      console.log(e);
    }
  }, [apiGet, setOrganizations, userLevel]);

  useEffect(() => {
    if (userLevel > 0) {
      fetchOrganizations();
    }
  }, [fetchOrganizations, userLevel]);

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
      users: GLOBAL_ADMIN,
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

  const orgPageMatch = useRouteMatch('/organizations/:id');

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

  const organizationDropdownOptions: Array<{ name: string }> = useMemo(() => {
    if (userLevel === GLOBAL_ADMIN) {
      return [{ name: 'All Organizations' }].concat(organizations);
    }
    if (userLevel === REGIONAL_ADMIN) {
      return organizations.filter((item) => {
        return item.regionId === user?.regionId;
      });
    }
    return [];
  }, [user, organizations, userLevel]);

  return (
    <Root>
      <AppBar position="static" elevation={0}>
        <div className={classes.inner}>
          <Toolbar>
            <img
              src={cisaLogo}
              className={classes.cisaLogo}
              alt="Cybersecurity and Infrastructure Security Agency Logo"
            />
            <Link to="/">
              <img
                src={logo}
                className={classes.logo}
                alt="CyHy Dashboard Icon Navigate Home"
              />
            </Link>
            {!isMobile && (
              <div className={classes.lgNav}>{desktopNavItems.slice()}</div>
            )}
            <div className={classes.spacing} />
            {userLevel > 0 && (
              <>{!isMobile && <UserMenu userMenuItems={userMenuItems} />}</>
            )}
            {user && isMobile && (
              <IconButton
                edge="start"
                className={classes.menuButton}
                aria-label="toggle mobile menu"
                color="inherit"
                onClick={toggleDrawer(true)}
              >
                <MenuIcon />
              </IconButton>
            )}
          </Toolbar>
        </div>
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
        <List className={classes.mobileNav}>
          {drawerItems.map(({ title, path }) => (
            <React.Fragment key={title.toString()}>
              {path && (
                <ListItem
                  // button
                  exact
                  component={NavLink}
                  to={path}
                  activeClassName={classes.activeMobileLink}
                  // onClick={onClick ? onClick : undefined}
                >
                  {title}
                </ListItem>
              )}
              {/* {nested?.map((nested) => (
                <ListItem
                  button
                  exact
                  key={nested.title.toString()}
                  component={NavLink}
                  to={nested.onClick ? '#' : nested.path}
                  activeClassName={classes.activeMobileLink}
                  onClick={nested.onClick ? nested.onClick : undefined}
                >
                  {nested.title}
                </ListItem>
              ))} */}
            </React.Fragment>
          ))}
        </List>
      </Drawer>
    </Root>
  );
};
