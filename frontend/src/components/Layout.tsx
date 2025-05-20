import React, {
  PropsWithChildren,
  useCallback,
  useEffect,
  useState
} from 'react';
import { styled } from '@mui/material/styles';
import { useLocation } from 'react-router-dom';
import { GovBanner, Header } from 'components';
import { useUserActivityTimeout } from 'hooks/useUserActivityTimeout';
import { useAuthContext } from 'context/AuthContext';
import UserInactiveModal from './UserInactivityModal/UserInactivityModal';
import { matchPath } from 'utils/matchPath';
import { FilterDrawerV2 } from './FilterDrawerV2';
import { withSearch } from '@elastic/react-search-ui';
import { ContextType } from 'context';
import { useUserTypeFilters } from 'hooks/useUserTypeFilters';
import { useStaticsContext } from 'context/StaticsContext';
import { useFilterDrawerContext } from 'context/FilterDrawerContext';
import { useUserLevel } from 'hooks/useUserLevel';

const Main = styled('main', {
  shouldForwardProp: (prop) => prop !== 'open' && prop !== 'user'
})<{
  open?: boolean;
  user?: boolean;
  // }>(({ theme, open, user }) => ({
}>(() => ({
  flexGrow: 1,
  minHeight: '100vh',
  height: '100vh',
  overflowY: 'auto'
  // transition: theme.transitions.create('margin', {
  //   easing: theme.transitions.easing.sharp,
  //   duration: theme.transitions.duration.leavingScreen
  // }),
  // [theme.breakpoints.up('lg')]: {
  //   marginLeft: `-${drawerWidth}px`
  // },
  // [theme.breakpoints.down('lg')]: {
  //   marginLeft: user ? 0 : `-${drawerWidth}px`
  // },
  // marginLeft: `-${drawerWidth}px`
  // ...(open && {
  //   transition: theme.transitions.create('margin', {
  //     easing: theme.transitions.easing.easeOut,
  //     duration: theme.transitions.duration.enteringScreen
  //   }),
  //   [theme.breakpoints.up('lg')]: {
  //     marginLeft: 0
  //   }
  // })
}));

export const Layout: React.FC<PropsWithChildren<ContextType>> = ({
  children,
  filters,
  addFilter
  // removeFilter
}) => {
  const { logout, user } = useAuthContext();

  useEffect(() => {
    localStorage.setItem('es-search-filters', JSON.stringify(filters));
  }, [filters]);

  const { regions } = useStaticsContext();

  const [initialFilters, setInitialFilters] = useState<any[]>([]);

  const { isFilterDrawerOpen, setIsFilterDrawerOpen } =
    useFilterDrawerContext();

  const userLevel = useUserLevel().userLevel;

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
  }, [pathname, setIsFilterDrawerOpen]);

  useEffect(() => {
    // set logged in if use exists then set true, otherwise set false
    if (user) setLoggedIn(true);
    else setLoggedIn(false);
  }, [user]);

  const initialFiltersForUser = useUserTypeFilters(regions, user, userLevel);

  useEffect(() => {
    initialFiltersForUser.forEach((filter) => {
      filter.values.forEach((val) => {
        addFilter(filter.field, val, filter.type);
      });
      setInitialFilters(initialFiltersForUser);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regions, user]);

  // const isMobile = useMediaQuery(theme.breakpoints.down('lg'));

  return (
    <>
      <UserInactiveModal
        isOpen={isTimedOut}
        onCountdownEnd={handleCountdownEnd}
        countdown={60} // 60 second timer for user inactivity timeout
      />
      <div style={{ display: 'flex' }}>
        <GovBanner />
      </div>
      <>
        <div
          style={{
            display: 'flex',
            flexDirection: 'row',
            height: '100vh'
          }}
        >
          {userLevel > 0 && (
            <FilterDrawerV2
              setIsFilterDrawerOpen={setIsFilterDrawerOpen}
              isFilterDrawerOpen={isFilterDrawerOpen}
              // isMobile={isMobile}
              initialFilters={initialFilters}
            />
          )}
          <Main open={isFilterDrawerOpen} user={!!user}>
            <Header />
            <div className="main-content" id="main-content" tabIndex={-1} />
            {children}
          </Main>
        </div>
      </>
    </>
  );
};

export const LayoutWithSearch = withSearch(
  ({ addFilter, removeFilter, filters }: ContextType) => ({
    addFilter,
    removeFilter,
    filters
  })
)(Layout);
