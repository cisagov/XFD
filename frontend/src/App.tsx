// frontend/src/App.tsx
import React, { useEffect } from 'react';
import { BrowserRouter as Router, useLocation } from 'react-router-dom';
import { API, Auth } from 'aws-amplify';
import { AuthContextProvider, CFThemeProvider, SearchProvider } from 'context';
import {
  MatomoProvider,
  createInstance,
  useMatomo
} from '@jonkoops/matomo-tracker-react';
import { LayoutWithSearch, Routes, MatomoTracker } from 'components';
import './styles.scss';
import { Authenticator } from '@aws-amplify/ui-react';
import { StaticsContextProvider } from 'context/StaticsContextProvider';
import { SavedSearchContextProvider } from 'context/SavedSearchContextProvider';
import { FilterDrawerContextProvider } from 'context/FilterDrawerContextProvider';
import { NavigationProvider } from 'context/NavigationContextProvider';
import { DevInspector } from './utils/devInspector';
import { openInVSCode } from './utils/openInVSCode';
import AppGate from './components/Gates/AppGate';

API.configure({
  endpoints: [{ name: 'crossfeed', endpoint: import.meta.env.VITE_API_URL }]
});

if (import.meta.env.VITE_USE_COGNITO) {
  Auth.configure({
    region: import.meta.env.VITE_EMAIL_REGION,
    userPoolId: import.meta.env.VITE_USER_POOL_ID,
    userPoolWebClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID
  });
}

const instance = createInstance({
  urlBase: `${import.meta.env.VITE_API_URL}/matomo`,
  siteId: 1,
  disabled: false,
  heartBeat: { active: true, seconds: 15 },
  linkTracking: false
});

const LinkTracker = () => {
  const location = useLocation();
  const { trackPageView } = useMatomo();
  useEffect(() => trackPageView({}), [location, trackPageView]);
  return null;
};

const App: React.FC = () => (
  <MatomoProvider value={instance}>
    <MatomoTracker />
    <Router>
      <CFThemeProvider>
        <AuthContextProvider>
          <Authenticator.Provider>
            <StaticsContextProvider>
              <SavedSearchContextProvider>
                <SearchProvider>
                  <FilterDrawerContextProvider>
                    <NavigationProvider>
                      <LayoutWithSearch>
                        <AppGate>
                          <LinkTracker />
                          <DevInspector
                            onClickElement={openInVSCode}
                          ></DevInspector>
                          <Routes />
                        </AppGate>
                      </LayoutWithSearch>
                    </NavigationProvider>
                  </FilterDrawerContextProvider>
                </SearchProvider>
              </SavedSearchContextProvider>
            </StaticsContextProvider>
          </Authenticator.Provider>
        </AuthContextProvider>
      </CFThemeProvider>
    </Router>
  </MatomoProvider>
);

export default App;
