import React, { useEffect } from 'react';
import {
  BrowserRouter as Router,
  Switch,
  Route,
  useLocation
} from 'react-router-dom';
import { API, Auth } from 'aws-amplify';
import { AuthContextProvider, CFThemeProvider, SearchProvider } from 'context';
import {
  MatomoProvider,
  createInstance,
  useMatomo
} from '@jonkoops/matomo-tracker-react';
import {
  AdminTools,
  AuthCreateAccount,
  AuthLogin,
  Domain,
  Domains,
  Feeds,
  LoginGovCallback,
  OktaCallback,
  RegionUsers,
  Reports,
  Organization,
  Organizations,
  SearchPage,
  Settings,
  TermsOfUse,
  Users,
  Vulnerabilities,
  Vulnerability
} from 'pages';
import { LayoutWithSearch, RouteGuard } from 'components';
import './styles.scss';
import { Authenticator } from '@aws-amplify/ui-react';
import { RSCDashboard } from 'components/ReadySetCyber/RSCDashboard';
import { RSCDetail } from 'components/ReadySetCyber/RSCDetail';
import { RSCLogin } from 'components/ReadySetCyber/RSCLogin';
import { RiskWithSearch } from 'pages/Risk/Risk';
import { StaticsContextProvider } from 'context/StaticsContextProvider';
import { SavedSearchContextProvider } from 'context/SavedSearchContextProvider';

API.configure({
  endpoints: [
    {
      name: 'crossfeed',
      endpoint: process.env.REACT_APP_API_URL
    }
  ]
});

if (process.env.REACT_APP_USE_COGNITO) {
  Auth.configure({
    region: process.env.EMAIL_REGION,
    userPoolId: process.env.REACT_APP_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID
  });
}

const instance = createInstance({
  urlBase: `${process.env.REACT_APP_API_URL}/matomo`,
  siteId: 1,
  disabled: false,
  heartBeat: {
    // optional, enabled by default
    active: true, // optional, default value: true
    seconds: 15 // optional, default value: `15
  },
  linkTracking: false // optional, default value: true
  // configurations: { // optional, default value: {}
  //   // any valid matomo configuration, all below are optional
  //   disableCookies: true,
  //   setSecureCookie: true,
  //   setRequestMethod: 'POST'
  // }
});

const LinkTracker = () => {
  const location = useLocation();
  const { trackPageView } = useMatomo();

  useEffect(() => trackPageView({}), [location, trackPageView]);

  return null;
};

const App: React.FC = () => (
  <MatomoProvider value={instance}>
    <Router>
      <CFThemeProvider>
        <AuthContextProvider>
          <Authenticator.Provider>
            <StaticsContextProvider>
              <SavedSearchContextProvider>
                <SearchProvider>
                  <LayoutWithSearch>
                    <LinkTracker />
                    <Switch>
                      <RouteGuard
                        exact
                        path="/"
                        unauth={AuthLogin}
                        component={RiskWithSearch}
                      />
                      <Route
                        exact
                        path="/login-gov-callback"
                        component={LoginGovCallback}
                      />
                      <Route
                        exact
                        path="/okta-callback"
                        component={OktaCallback}
                      />
                      <Route
                        exact
                        path="/create-account"
                        component={AuthCreateAccount}
                      />
                      <Route exact path="/terms" component={TermsOfUse} />
                      <RouteGuard
                        exact
                        path="/inventory"
                        component={SearchPage}
                        permissions={[
                          'globalView',
                          'regionalAdmin',
                          'standard'
                        ]}
                      />
                      <RouteGuard
                        path="/inventory/domain/:domainId"
                        component={Domain}
                        permissions={[
                          'globalView',
                          'regionalAdmin',
                          'standard'
                        ]}
                      />
                      <RouteGuard
                        path="/inventory/domains"
                        component={Domains}
                      />
                      <RouteGuard
                        path="/inventory/vulnerabilities"
                        exact
                        component={Vulnerabilities}
                        permissions={[
                          'globalView',
                          'regionalAdmin',
                          'standard'
                        ]}
                      />
                      <RouteGuard
                        path="/inventory/vulnerabilities/grouped"
                        component={(props) => (
                          <Vulnerabilities {...props} groupBy="title" />
                        )}
                        permissions={[
                          'globalView',
                          'regionalAdmin',
                          'standard'
                        ]}
                      />
                      <RouteGuard
                        path="/inventory/vulnerability/:vulnerabilityId"
                        component={Vulnerability}
                        permissions={[
                          'globalView',
                          'regionalAdmin',
                          'standard'
                        ]}
                      />
                      <RouteGuard
                        path="/feeds"
                        component={Feeds}
                        permissions={['globalView']}
                      />
                      <RouteGuard
                        path="/reports"
                        component={Reports}
                        permissions={[
                          'globalView',
                          'regionalAdmin',
                          'standard'
                        ]}
                      />
                      <RouteGuard path="/admin-tools" component={AdminTools} />
                      <RouteGuard
                        path="/organizations/:organizationId"
                        component={Organization}
                        permissions={['globalView', 'regionalAdmin']}
                      />
                      <RouteGuard
                        path="/organizations"
                        component={Organizations}
                        permissions={[
                          'globalView',
                          'regionalAdmin',
                          'standard'
                        ]}
                      />
                      <RouteGuard
                        path="/users"
                        component={Users}
                        permissions={['globalView', 'regionalAdmin']}
                      />
                      <RouteGuard
                        path="/settings"
                        component={Settings}
                        permissions={[
                          'globalView',
                          'regionalAdmin',
                          'standard'
                        ]}
                      />
                      <RouteGuard
                        path="/region-admin-dashboard"
                        component={RegionUsers}
                        permissions={['regionalAdmin', 'globalView']}
                      />
                      <RouteGuard
                        exact
                        path="/readysetcyber"
                        unauth={RSCLogin}
                        component={RSCDashboard}
                      />
                      <RouteGuard
                        exact
                        path="/readysetcyber/dashboard"
                        component={RSCDashboard}
                        permissions={[
                          'globalView',
                          'readySetCyber',
                          'regionalAdmin',
                          'standard'
                        ]}
                        unauth={RSCLogin}
                      />
                      <RouteGuard
                        path="/readysetcyber/result/:id"
                        component={RSCDetail}
                        permissions={[
                          'globalView',
                          'readySetCyber',
                          'regionalAdmin',
                          'standard'
                        ]}
                        unauth={RSCLogin}
                      />
                    </Switch>
                  </LayoutWithSearch>
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
