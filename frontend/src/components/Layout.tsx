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
import { FilterDrawerV2 } from './FilterDrawer/FilterDrawerV2';
import { withSearch } from '@elastic/react-search-ui';
import { ContextType } from 'context';
import { useUserTypeFilters } from 'hooks/useUserTypeFilters';
import { useStaticsContext } from 'context/StaticsContext';
import { useFilterDrawerContext } from 'context/FilterDrawerContext';
import { useUserLevel } from 'hooks/useUserLevel';
import { useTheme } from '@mui/material/styles';
import { useMediaQuery } from '@mui/system';
import FilterDrawerToggle from './FilterDrawer/FilterDrawerToggle';

const Main = styled('main', {
  shouldForwardProp: (prop) => prop !== 'open' && prop !== 'user'
})<{
  open?: boolean;
  user?: boolean;
}>(() => ({
  flexGrow: 1,
  minHeight: '100vh',
  height: '100vh',
  overflowY: 'auto',
  overscrollBehavior: 'contain'
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

  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('lg'));

  return (
    <>
      <UserInactiveModal
        isOpen={isTimedOut}
        onCountdownEnd={handleCountdownEnd}
        countdown={60} // 60 second timer for user inactivity timeout
      />
      <Main open={isFilterDrawerOpen} user={!!user}>
        <div style={{ display: 'flex' }}>
          <GovBanner />
        </div>
        <Header />
        {userLevel > 0 && (
          <>
            {matchPath(['/', '/inventory', '/VSDashboard'], pathname) && (
              <FilterDrawerToggle />
            )}
            <FilterDrawerV2
              setIsFilterDrawerOpen={setIsFilterDrawerOpen}
              isFilterDrawerOpen={isFilterDrawerOpen}
              isMobile={isMobile}
              initialFilters={initialFilters}
            />
          </>
        )}
        {children}
      </Main>
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
