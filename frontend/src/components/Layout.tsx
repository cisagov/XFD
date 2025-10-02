import React, {
  PropsWithChildren,
  useCallback,
  useEffect,
  useRef,
  useState
} from 'react';
import { useLocation } from 'react-router-dom';
import { withSearch } from '@elastic/react-search-ui';
import { Alert, AlertTitle, Box, Typography } from '@mui/material';
import { styled, useTheme } from '@mui/material/styles';
import { useMediaQuery } from '@mui/system';
import { GovBanner, Header } from 'components';
import { useUserActivityTimeout } from 'hooks/useUserActivityTimeout';
import { useAuthContext } from 'context/AuthContext';
import UserInactiveModal from './UserInactivityModal/UserInactivityModal';
import { matchPath } from 'utils/matchPath';
import { FilterDrawerV2 } from './FilterDrawer/FilterDrawerV2';
import { ContextType } from 'context';
import { useUserTypeFilters } from 'hooks/useUserTypeFilters';
import { useStaticsContext } from 'context/StaticsContext';
import { useFilterDrawerContext } from 'context/FilterDrawerContext';
import { useUserLevel } from 'hooks/useUserLevel';
import FilterDrawerToggle from './FilterDrawer/FilterDrawerToggle';
import { useFilterRestore } from 'hooks/useFilterRestore';
import { FILTER_ENABLED_PATHS } from 'constants/filterPaths';
import { useNavigationContext, isVSDashboard } from 'context/NavigationContext';

const Main = styled('main', {
  shouldForwardProp: (prop) =>
    prop !== 'open' && prop !== 'user' && prop !== 'topOffset'
})<{
  open?: boolean;
  user?: boolean;
  topOffset?: number;
}>(({ topOffset }) => ({
  minHeight: '100vh',
  overflowY: 'auto',
  overscrollBehavior: 'contain',
  paddingTop: topOffset ?? 0
}));

export const Layout: React.FC<PropsWithChildren<ContextType>> = ({
  children,
  filters,
  addFilter
  // removeFilter
}) => {
  const { pathname } = useLocation();
  const { logout, user } = useAuthContext();
  const { isDrillDown } = useNavigationContext();
  const topRef = useRef<HTMLDivElement>(null);
  const [topOffset, setTopOffset] = useState(0);

  // Restore filters from localStorage when navigating to filter-enabled pages
  useFilterRestore(filters, addFilter, pathname);

  const noAlertPaths = [
    '/login-gov-callback',
    '/okta-callback',
    '/create-account',
    '/terms'
  ];

  useEffect(() => {
    // NEW LOGIC: Only store filters during drill-down scenarios or on non-VS Dashboard pages
    // - If we're on VS Dashboard and NOT in drill-down context, don't store filters 
    //   (this prevents persistence of user-default filters that should reset on reload)
    // - If we're in drill-down context, always store filters for restoration
    // - If we're on other pages, store filters as usual
    
    const isVSDashboardPath = isVSDashboard(pathname);
    
    if (isVSDashboardPath && !isDrillDown) {
      console.log('[Layout] VS Dashboard without drill-down context, not storing filters');
      return;
    }
    
    console.log(`[Layout] Storing filters for ${pathname}, isDrillDown: ${isDrillDown}, filterCount: ${filters.length}`);
    
    // For VS Dashboard in drill-down context, filter out region filters to allow reset to user defaults on page reload
    const filtersToStore = isVSDashboardPath 
      ? filters.filter(filter => filter.field !== 'organization.region_id')
      : filters;
    
    localStorage.setItem('es-search-filters', JSON.stringify(filtersToStore));
  }, [filters, pathname, isDrillDown]);

  const { regions } = useStaticsContext();

  const [initialFilters, setInitialFilters] = useState<any[]>([]);

  const { isFilterDrawerOpen, setIsFilterDrawerOpen } =
    useFilterDrawerContext();

  const [siteWideAlert, setSiteWideAlert] = useState(() => {
    return localStorage.getItem('siteWideAlertOff') === 'true';
  });

  useEffect(() => {
    if (topRef.current) {
      setTopOffset(topRef.current.getBoundingClientRect().height);
    }
  }, [siteWideAlert, user, pathname]);

  const handleAlertClose = () => {
    setSiteWideAlert(true);
    localStorage.setItem('siteWideAlertOff', 'true');
  };

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

  useEffect(() => {
    if (!matchPath(FILTER_ENABLED_PATHS, pathname)) {
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
    // Skip automatic user type filters on VS Dashboard - it has custom filter logic
    const isVSDashboardPath = isVSDashboard(pathname);
    if (isVSDashboardPath) {
      return;
    }
    
    initialFiltersForUser.forEach((filter) => {
      filter.values.forEach((val) => {
        addFilter(filter.field, val, filter.type);
      });
      setInitialFilters(initialFiltersForUser);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regions, user, pathname]);

  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('lg'));

  return (
    <>
      <UserInactiveModal
        isOpen={isTimedOut}
        onCountdownEnd={handleCountdownEnd}
        countdown={60}
      />
      <Box
        ref={topRef}
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: (theme) => theme.zIndex.appBar
        }}
      >
        <GovBanner />
        {!siteWideAlert && user && !noAlertPaths.includes(pathname) && (
          <Box sx={{ backgroundColor: '#E5F6FD' }}>
            <Box
              display="flex"
              flexDirection="column"
              maxWidth="1152px"
              width="100%"
              margin="auto"
            >
              <Alert severity="info" onClose={handleAlertClose}>
                <AlertTitle
                  variant="largeBody"
                  color="primary.darker"
                  sx={{ fontWeight: '700' }}
                >
                  CyHy Dashboard - Beta (Early Access)
                </AlertTitle>
                <Typography
                  variant="body1"
                  color="primary.darker"
                  fontWeight="600"
                >
                  You are using an early release version of the CyHy Dashboard.
                  This site is fully functional, but some features are still
                  being improved and refined. Your feedback during this stage
                  directly shapes improvements. Please go to the Support menu to
                  share feedback, report bugs, or submit questions so we can
                  enhance the dashboard to better meet your needs.
                </Typography>
              </Alert>
            </Box>
          </Box>
        )}
        <Header />
        {userLevel > 0 &&
          matchPath(FILTER_ENABLED_PATHS, pathname) && (
            <FilterDrawerToggle />
          )}
      </Box>
      <Main open={isFilterDrawerOpen} user={!!user} topOffset={topOffset}>
        {userLevel > 0 &&
          matchPath(FILTER_ENABLED_PATHS, pathname) && (
            <FilterDrawerV2
              setIsFilterDrawerOpen={setIsFilterDrawerOpen}
              isFilterDrawerOpen={isFilterDrawerOpen}
              isMobile={isMobile}
              initialFilters={initialFilters}
              topOffset={topOffset}
            />
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
