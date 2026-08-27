// frontend/src/App.tsx
import React, { useEffect } from 'react';
import { BrowserRouter as Router, useLocation } from 'react-router-dom';
import { AuthContextProvider, CFThemeProvider, SearchProvider } from 'context';
import { ROUTES } from '@/constants/routes';
import {
  MatomoProvider,
  createInstance,
  useMatomo
} from '@jonkoops/matomo-tracker-react';
import { LayoutWithSearch, Routes, MatomoTracker } from 'components';
import './styles.scss';
import { StaticsContextProvider } from 'context/StaticsContextProvider';
import { SavedSearchContextProvider } from 'context/SavedSearchContextProvider';
import { FilterDrawerContextProvider } from 'context/FilterDrawerContextProvider';
import { NavigationProvider } from 'context/NavigationContextProvider';
import { DevInspector } from './utils/devInspector';
import { openInVSCode } from './utils/openInVSCode';
import AppGate from './components/Gates/AppGate';
import TermsGate from './components/Gates/TermsGate';
import { MuiGlobalStyles } from 'context/MuiGlobalStyles';

const instance = createInstance({
  urlBase: `${import.meta.env.VITE_API_URL}${ROUTES.MATOMO}`,
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
        <MuiGlobalStyles />
        <AuthContextProvider>
          <TermsGate>
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
          </TermsGate>
        </AuthContextProvider>
      </CFThemeProvider>
    </Router>
  </MatomoProvider>
);

export default App;
