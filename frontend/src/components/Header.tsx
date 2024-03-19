import React, { useState } from 'react';
import { styled } from '@mui/material/styles';
import { NavLink, Link, useHistory, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  IconButton,
  Drawer,
  ListItem,
  List
} from '@mui/material';
import { Menu as MenuIcon } from '@mui/icons-material';
import { NavItem } from './NavItem';
import { useAuthContext } from 'context';
import logo from '../assets/crossfeed.svg';
import { withSearch } from '@elastic/react-search-ui';
import { ContextType } from 'context/SearchProvider';
import { SearchBar } from 'components';

const PREFIX = 'Header';

const classes = {
  inner: `${PREFIX}-inner`,
  menuButton: `${PREFIX}-menuButton`,
  logo: `${PREFIX}-logo`,
  spacing: `${PREFIX}-spacing`,
  activeMobileLink: `${PREFIX}-activeMobileLink`,
  link: `${PREFIX}-link`,
  lgNav: `${PREFIX}-lgNav`,
  mobileNav: `${PREFIX}-mobileNav`,
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
    display: 'flex',
    [theme.breakpoints.up('xl')]: {
      display: 'none'
    }
  },

  [`.${classes.logo}`]: {
    width: 150,
    minWidth: 150,
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
  [`.${classes.lgNav}`]: {
    display: 'flex',
    [theme.breakpoints.down('sm')]: {
      display: 'flex'
    }
  },

  [`.${classes.mobileNav}`]: {
    padding: `${theme.spacing(2)} ${theme.spacing()}px`
  }
}));

const GLOBAL_ADMIN = 2;
const STANDARD_USER = 1;
const ALL_USERS = GLOBAL_ADMIN | STANDARD_USER;

interface NavItemType {
  title: string | JSX.Element;
  path: string;
  users?: number;
  nested?: NavItemType[];
  onClick?: any;
  exact: boolean;
}

const HeaderNoCtx: React.FC<ContextType> = (props) => {
  const { searchTerm, setSearchTerm } = props;

  const history = useHistory();
  const location = useLocation();
  const { user, logout } = useAuthContext();
  const [navOpen, setNavOpen] = useState(false);

  let userLevel = 0;
  if (user && user.isRegistered) {
    if (user.userType === 'standard') {
      userLevel = STANDARD_USER;
    } else {
      userLevel = GLOBAL_ADMIN;
    }
  }

  const navItems: NavItemType[] = [
    {
      title: 'Overview',
      path: '/',
      users: ALL_USERS,
      exact: true
    },
    {
      title: 'Inventory',
      path: '/inventory',
      users: ALL_USERS,
      exact: false
    },
    {
      title: 'Scans',
      path: '/scans',
      users: GLOBAL_ADMIN,
      exact: true
    }
  ].filter(({ users }) => (users & userLevel) > 0);

  const userItems: NavItemType[] = [
    {
      title: 'My Account',
      path: '#',
      users: ALL_USERS,
      exact: false
    },
    {
      title: 'Manage Organizations',
      path: '/organizations',
      users: GLOBAL_ADMIN,
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
      users: ALL_USERS,
      exact: true
    },
    {
      title: 'Logout',
      path: '/',
      users: ALL_USERS,
      onClick: logout,
      exact: true
    }
  ].filter(({ users }) => (users & userLevel) > 0);

  const desktopNavItems: JSX.Element[] = navItems.map((item) => (
    <NavItem key={item.title.toString()} {...item} />
  ));

  return (
    <Root>
      <AppBar position="static" elevation={0}>
        <div className={classes.inner}>
          <Toolbar>
            <Link to="/">
              <img
                src={logo}
                className={classes.logo}
                alt="Crossfeed Icon Navigate Home"
              />
            </Link>
            <div className={classes.lgNav}>{desktopNavItems.slice()}</div>
            <div className={classes.spacing} />

            {userLevel > 0 && (
              <>
                <SearchBar
                  initialValue={searchTerm}
                  value={searchTerm}
                  onChange={(value) => {
                    if (location.pathname !== '/inventory')
                      history.push('/inventory?q=' + value);
                    setSearchTerm(value, {
                      shouldClearFilters: false,
                      autocompleteResults: false
                    });
                  }}
                />
                <IconButton
                  edge="start"
                  className={classes.menuButton}
                  aria-label="toggle mobile menu"
                  color="inherit"
                  onClick={() => setNavOpen((open) => !open)}
                >
                  <MenuIcon />
                </IconButton>
              </>
            )}
          </Toolbar>
        </div>
      </AppBar>
      <Drawer
        anchor="right"
        open={navOpen}
        onClose={() => setNavOpen(false)}
        data-testid="mobilenav"
      >
        <List className={classes.mobileNav}>
          {userItems.map(({ title, path, nested, onClick }) => (
            <React.Fragment key={title.toString()}>
              {path && (
                <ListItem
                  button
                  exact
                  component={NavLink}
                  to={path}
                  activeClassName={classes.activeMobileLink}
                  onClick={onClick ? onClick : undefined}
                >
                  {title}
                </ListItem>
              )}
              {nested?.map((nested) => (
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
              ))}
            </React.Fragment>
          ))}
        </List>
      </Drawer>
    </Root>
  );
};

export const Header = withSearch(
  ({ searchTerm, setSearchTerm }: ContextType) => ({
    searchTerm,
    setSearchTerm
  })
)(HeaderNoCtx);
