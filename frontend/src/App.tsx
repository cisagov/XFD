// frontend/src/App.tsx
import React, { useEffect } from 'react';
import { BrowserRouter as Router, useLocation } from 'react-router-dom';

// Matomo Tracker
import {
  MatomoProvider,
  createInstance,
  useMatomo
} from '@jonkoops/matomo-tracker-react';

// Components
import { LayoutWithSearch, Routes, MatomoTracker } from '@/components';
import AppGate from '@/components/Gates/AppGate';
import TermsGate from '@/components/Gates/TermsGate';

// Constants
import { ROUTES } from '@/constants/routes';

// Context
import {
  AuthContextProvider,
  CFThemeProvider,
  SearchProvider
} from '@/context';
import { FilterDrawerContextProvider } from '@/context/FilterDrawerContextProvider';
import { MuiGlobalStyles } from '@/context/MuiGlobalStyles';
import { NavigationProvider } from '@/context/NavigationContextProvider';
import { SavedSearchContextProvider } from '@/context/SavedSearchContextProvider';
import { StaticsContextProvider } from '@/context/StaticsContextProvider';

// Utils
import { DevInspector } from '@/utils/devInspector';
import { openInVSCode } from '@/utils/openInVSCode';

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
