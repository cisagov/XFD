import React from 'react';
import { Route, Switch } from 'react-router-dom';
import { RouteGuard } from 'components/Routes/RouteGuard';
import {
  AdminTools,
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
import { VulnerabilityScanWithSearch } from '../Gates/VSDashboardGate';

export const Routes: React.FC = () => {
  return (
    <Switch>
      <RouteGuard
        exact
        path="/"
        unauth={AuthLogin}
        component={VulnerabilityScanWithSearch}
      />
      <Route exact path="/login-gov-callback" component={LoginGovCallback} />
      <Route exact path="/okta-callback" component={OktaCallback} />
      <Route exact path="/terms" component={TermsOfUse} />
      <RouteGuard
        exact
        path="/inventory"
        component={SearchPage}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path="/inventory/domain/:domainId"
        component={Domain}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard path="/inventory/domains" component={Domains} />
      <RouteGuard path="/VSDashboard" component={VulnerabilityScanWithSearch} />
      <RouteGuard
        exact
        path="/inventory/vulnerabilities"
        component={Vulnerabilities}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path="/inventory/vulnerabilities/grouped"
        component={(props) => <Vulnerabilities {...props} group_by="title" />}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path="/inventory/vulnerability/:vulnerabilityId"
        component={Vulnerability}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path="/feeds"
        component={Feeds}
        permissions={['globalView']}
      />
      <RouteGuard
        path="/reports"
        component={Reports}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path="/admin-tools"
        component={AdminTools}
        permissions={['globalAdmin']}
      />
      <RouteGuard
        path="/organizations/:organizationId"
        component={Organization}
        permissions={['globalView', 'regionalAdmin']}
      />
      <RouteGuard
        path="/organizations"
        component={Organizations}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path="/users"
        component={Users}
        permissions={['globalView', 'regionalAdmin']}
      />
      <RouteGuard
        path="/settings"
        component={Settings}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path="/region-admin-dashboard"
        component={RegionUsers}
        permissions={['regionalAdmin', 'globalView']}
      />
    </Switch>
  );
};
