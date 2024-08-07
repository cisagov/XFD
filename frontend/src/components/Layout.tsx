import React, { useEffect, useState } from 'react';
import { styled } from '@mui/material/styles';
import { useLocation } from 'react-router-dom';
import { Box, Drawer, ScopedCssBaseline } from '@mui/material';
import { Header, GovBanner } from 'components';
import { useUserActivityTimeout } from 'hooks/useUserActivityTimeout';
import { useAuthContext } from 'context/AuthContext';
import UserInactiveModal from './UserInactivityModal/UserInactivityModal';
import { CrossfeedFooter } from './Footer';
import { RSCFooter } from './ReadySetCyber/RSCFooter';
import { RSCHeader } from './ReadySetCyber/RSCHeader';
import { SkipToMainContent } from './SkipToMainContent/index';
import { SideDrawerWithSearch } from './SideDrawer';
import { matchPath } from 'utils/matchPath';
import { drawerWidth, FilterDrawerV2 } from './FilterDrawerV2';
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
  transition: theme.transitions.create('margin', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  marginLeft: `-${drawerWidth}px`,
  ...(open && {
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
    marginLeft: 0,
  }),
}));


export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { logout, user } = useAuthContext();
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = useState(false)
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
  const [loggedIn, setLoggedIn] = useState<boolean>(
    user !== null && user !== undefined ? true : false
  );
  const { isTimedOut, resetTimeout } = useUserActivityTimeout(
    14 * 60 * 1000, // set to 14 minutes of inactivity to notify user
    loggedIn
  );

  const handleCountdownEnd = (shouldLogout: boolean) => {
    if (shouldLogout) {
      logout();
    } else {
      resetTimeout();
    }
  };

  const { pathname } = useLocation();

  useEffect(() => {
    // set logged in if use exists then set true, otherwise set false
    if (user) setLoggedIn(true);
    else setLoggedIn(false);
  }, [user]);

  

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
                height: '100vh',
              }}
            >
              {userLevel > 0 &&
              (matchPath(['/', '/inventory', '/inventory/domains', '/inventory/vulnerabilities'], pathname)) ? (
                <FilterDrawerV2 isFilterDrawerOpen={isFilterDrawerOpen} />
              ) : <Drawer open={false} variant='persistent' sx={{ width: drawerWidth }}/>}
              <Main open={isFilterDrawerOpen}>
                  <Header isFilterDrawerOpen={isFilterDrawerOpen} setIsFilterDrawerOpen={setIsFilterDrawerOpen} />
                
                <Box display='block' position='relative' flex='1' height='calc(100vh - 64px - 72px - 24px)' overflow='scroll' zIndex={16}>
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
