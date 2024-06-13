import React, { useCallback, useEffect, useState } from 'react';
import { styled } from '@mui/material/styles';
import { useLocation } from 'react-router-dom';
import { Alert, ScopedCssBaseline } from '@mui/material';
import { Header, GovBanner } from 'components';
import { useUserActivityTimeout } from 'hooks/useUserActivityTimeout';
import { useAuthContext } from 'context/AuthContext';
import UserInactiveModal from './UserInactivityModal/UserInactivityModal';
import { CrossfeedFooter } from './Footer';
import { RSCFooter } from './ReadySetCyber/RSCFooter';
import { RSCHeader } from './ReadySetCyber/RSCHeader';

interface LayoutProps {
  children: React.ReactNode;
}

const parseTextToJSX = (text: String) => {
  const lines = text.split('\n');
  return lines.map((line, index) => {
    const parts = line.split(/(\[.*?\]\(.*?\))/g).map((part, i) => {
      const match = part.match(/\[(.*?)\]\((.*?)\)/);
      if (match) {
        return (
          <a
            key={i}
            href={match[2]}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={match[2]}
          >
            {match[1]}
          </a>
        );
      }
      return part;
    });
    return <div key={index}>{parts}</div>;
  });
};

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { apiGet, logout, user } = useAuthContext();
  const [loggedIn, setLoggedIn] = useState<boolean>(
    user !== null && user !== undefined ? true : false
  );
  const [warningBannerText, setWarningBannerText] = useState<JSX.Element[]>([]);
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

  const fetchWarningBannerText = useCallback(async () => {
    try {
      const text = await apiGet('/notifications/508-banner/');
      const parsedText = parseTextToJSX(text);
      setWarningBannerText(parsedText);
    } catch (e) {
      console.log(e);
    }
  }, [apiGet, setWarningBannerText]);

  useEffect(() => {
    fetchWarningBannerText();
  }, [fetchWarningBannerText]);

  return (
    <StyledScopedCssBaseline classes={{ root: classes.overrides }}>
      <div className={classes.root}>
        <UserInactiveModal
          isOpen={isTimedOut}
          onCountdownEnd={handleCountdownEnd}
          countdown={60} // 60 second timer for user inactivity timeout
        />
        <Alert severity="warning" aria-label="warning label">
          <div>{warningBannerText}</div>
        </Alert>
        <GovBanner />
        {!pathname.includes('/readysetcyber') ? (
          <>
            <Header />
            {pathname === '/inventory' ? (
              children
            ) : (
              <div className={classes.content}>{children}</div>
            )}
            <CrossfeedFooter />
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
    position: 'relative'
  }
}));
