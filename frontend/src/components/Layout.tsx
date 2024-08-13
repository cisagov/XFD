import React, {
  PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState
} from 'react';
import { styled } from '@mui/material/styles';
import { useLocation } from 'react-router-dom';
import { Box, Drawer, ScopedCssBaseline, useMediaQuery } from '@mui/material';
import { Header, GovBanner } from 'components';
import { useUserActivityTimeout } from 'hooks/useUserActivityTimeout';
import { useAuthContext } from 'context/AuthContext';
import UserInactiveModal from './UserInactivityModal/UserInactivityModal';
import { CrossfeedFooter } from './Footer';
import { RSCFooter } from './ReadySetCyber/RSCFooter';
import { RSCHeader } from './ReadySetCyber/RSCHeader';
import { SkipToMainContent } from './SkipToMainContent/index';
import { matchPath } from 'utils/matchPath';
import { drawerWidth, FilterDrawerV2 } from './FilterDrawerV2';
import { usePersistentState } from 'hooks';
import { useTheme } from '@mui/system';
import { withSearch } from '@elastic/react-search-ui';
import { ContextType } from 'context';
import { useUserTypeFilters } from 'hooks/useUserTypeFilters';
import { useStaticsContext } from 'context/StaticsContext';
interface LayoutProps {
  children: React.ReactNode;
}

const GLOBAL_ADMIN = 3;
const REGIONAL_ADMIN = 2;
const STANDARD_USER = 1;

const Main = styled('main', { shouldForwardProp: (prop) => prop !== 'open' })<{
  open?: boolean;
}>(({ theme, open }) => ({
  flexGrow: 1,
  height: 'calc(100vh - 24px)',
  maxHeight: 'calc(100vh - 24px)',
  overflow: 'scroll',
  '&::-webkit-scrollbar': {
    display: 'none'
  },
  transition: theme.transitions.create('margin', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen
  }),
  [theme.breakpoints.up('lg')]: {
    marginLeft: `-${drawerWidth}px`
  },
  [theme.breakpoints.down('lg')]: {
    marginLeft: 0
  },
  ...(open && {
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen
    }),
    [theme.breakpoints.up('lg')]: {
      marginLeft: 0
    },
    [theme.breakpoints.down('lg')]: {
      marginLeft: 0
    }
  })
}));

export const Layout: React.FC<PropsWithChildren<ContextType>> = ({
  children,
  filters,
  addFilter,
  removeFilter
}) => {
  const { logout, user } = useAuthContext();

  useEffect(() => {
    localStorage.setItem('es-search-filters', JSON.stringify(filters));
  }, [filters]);

  const { regions } = useStaticsContext();

  const theme = useTheme();
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = usePersistentState(
    'isFilterDrawerOpen',
    false
  );

  const userLevel = useMemo(() => {
    if (user && user.isRegistered) {
      if (user.userType === 'standard') {
        return STANDARD_USER;
      } else if (user.userType === 'globalAdmin') {
        return GLOBAL_ADMIN;
      } else if (
        user.userType === 'regionalAdmin' ||
        user.userType === 'globalView'
      ) {
        return REGIONAL_ADMIN;
      }
      return 0;
    }
    return 0;
  }, [user]);

  const [loggedIn, setLoggedIn] = useState<boolean>(
    user !== null && user !== undefined ? true : false
  );
  const { isTimedOut, resetTimeout } = useUserActivityTimeout(
    14 * 60 * 1000, // set to 14 minutes of inactivity to notify user
    loggedIn
  );

  const handleCountdownEnd = useCallback(
    (shouldLogout: boolean) => {
      if (shouldLogout) {
        logout();
      } else {
        resetTimeout();
      }
    },
    [logout, resetTimeout]
  );

  const { pathname } = useLocation();

  useEffect(() => {
    const pathsAllowed = ['/', '/inventory'];
    if (!matchPath(pathsAllowed, pathname)) {
      setIsFilterDrawerOpen(false);
    }
  }, [pathname]);

  useEffect(() => {
    // set logged in if use exists then set true, otherwise set false
    if (user) setLoggedIn(true);
    else setLoggedIn(false);
  }, [user]);

  const initialFiltersForUser = useUserTypeFilters(
    filters,
    addFilter,
    removeFilter,
    regions,
    user,
    userLevel
  );

  useEffect(() => {
    initialFiltersForUser.forEach((filter) => {
      filter.values.forEach((val) => {
        addFilter(filter.field, val, filter.type);
      });
    });
  }, [regions, user]);

  const isMobile = useMediaQuery(theme.breakpoints.down('lg'));

  return (
    <StyledScopedCssBaseline classes={{ root: classes.overrides }}>
      <div className={classes.root}>
        <UserInactiveModal
          isOpen={isTimedOut}
          onCountdownEnd={handleCountdownEnd}
          countdown={60} // 60 second timer for user inactivity timeout
        />
        <div style={{ display: 'flex' }}>
          <GovBanner />
          <SkipToMainContent />
        </div>
        {!pathname.includes('/readysetcyber') ? (
          <>
            <div
              style={{
                display: 'flex',
                flexDirection: 'row',
                height: '100vh'
              }}
            >
              {userLevel > 0 &&
              matchPath(
                [
                  '/',
                  '/inventory',
                  '/inventory/domains',
                  '/inventory/vulnerabilities'
                ],
                pathname
              ) ? (
                <FilterDrawerV2
                  setIsFilterDrawerOpen={setIsFilterDrawerOpen}
                  isFilterDrawerOpen={isFilterDrawerOpen}
                  isMobile={isMobile}
                />
              ) : (
                <Drawer sx={{ width: drawerWidth }} variant="persistent">
                  <Box sx={{ width: drawerWidth }} />
                </Drawer>
              )}
              <Main open={isFilterDrawerOpen}>
                <Header
                  isFilterDrawerOpen={isFilterDrawerOpen}
                  setIsFilterDrawerOpen={setIsFilterDrawerOpen}
                />

                <Box
                  display="block"
                  position="relative"
                  flex="1"
                  height="calc(100vh - 64px - 72px - 24px)"
                  overflow="scroll"
                  sx={{
                    '&::-webkit-scrollbar': {
                      display: 'none'
                    }
                  }}
                  zIndex={16}
                >
                  {children}
                </Box>

                {/* <div className="main-content" id="main-content" tabIndex={-1} />
                {pathname === '/inventory' ? (
                  children
                ) : (
                  <div className={classes.content}>{children}</div>
                )} */}

                <CrossfeedFooter />
              </Main>
            </div>
          </>
        ) : (
          <>
            <RSCHeader />
            <div className={classes.content}>{children}</div>
            <RSCFooter />
          </>
        )}
      </div>
    </StyledScopedCssBaseline>
  );
};

export const LayoutWithSearch = withSearch(
  ({ addFilter, removeFilter, filters }: ContextType) => ({
    addFilter,
    removeFilter,
    filters
  })
)(Layout);

//Styling
const PREFIX = 'Layout';

const classes = {
  root: `${PREFIX}-root`,
  overrides: `${PREFIX}-overrides`,
  content: `${PREFIX}-content`
};

const StyledScopedCssBaseline = styled(ScopedCssBaseline)(({ theme }) => ({
  [`& .${classes.root}`]: {
    position: 'relative',
    height: '100vh',
    display: 'flex',
    flexFlow: 'column nowrap'
    // overflow: 'auto'
  },

  [`& .${classes.overrides}`]: {
    WebkitFontSmoothing: 'unset',
    MozOsxFontSmoothing: 'unset'
  },

  [`& .${classes.content}`]: {
    flex: '1',
    display: 'block',
    position: 'relative',
    height: 'calc(100vh - 24px)',
    overflow: 'scroll'
  }
}));
