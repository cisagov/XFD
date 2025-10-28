import React from 'react';
import { Route, Switch } from 'react-router-dom';
import { RouteGuard } from 'components/Routes/RouteGuard';
import {
  AdminTools,
  AuthLogin,
  Domain,
  Domains,
  LoginGovCallback,
  OktaCallback,
  RegionUsers,
  Organization,
  Organizations,
  SearchPage,
  Settings,
  Users,
  Vulnerabilities,
  Vulnerability
} from 'pages';
import { VulnerabilityScanWithSearch } from '../Gates/VSDashboardGate';
import { ROUTES } from '@/constants/routes';

export const Routes: React.FC = () => {
  return (
    <Switch>
      <RouteGuard
        exact
        path={ROUTES.HOME}
        unauth={AuthLogin}
        component={VulnerabilityScanWithSearch}
      />
      <Route exact path={ROUTES.LOGIN} component={LoginGovCallback} />
      <Route exact path={ROUTES.OKTA_CALLBACK} component={OktaCallback} />
      <RouteGuard
        exact
        path={ROUTES.INVENTORY}
        component={SearchPage}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path={ROUTES.DOMAIN}
        component={Domain}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard path={ROUTES.DOMAINS} component={Domains} />
      <RouteGuard
        path={ROUTES.VSDASHBOARD}
        component={VulnerabilityScanWithSearch}
      />
      <RouteGuard
        exact
        path={ROUTES.VULNERABILITIES}
        component={Vulnerabilities}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path={ROUTES.VULNERABILITIES_GROUPED}
        component={(props) => <Vulnerabilities {...props} group_by="title" />}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path={ROUTES.VULNERABILITY}
        component={Vulnerability}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path={ROUTES.ADMIN_TOOLS}
        component={AdminTools}
        permissions={['globalAdmin']}
      />
      <RouteGuard
        path={ROUTES.ORGANIZATION}
        component={Organization}
        permissions={['globalView', 'regionalAdmin']}
      />
      <RouteGuard
        path={ROUTES.ORGANIZATIONS}
        component={Organizations}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      <RouteGuard
        path={ROUTES.USERS}
        component={Users}
        permissions={['globalView', 'regionalAdmin']}
      />
      <RouteGuard
        path={ROUTES.SETTINGS}
        component={Settings}
        permissions={['globalView', 'regionalAdmin', 'standard']}
      />
      {/* Multiple paths for user registration dashboard - Dynamic routes will not work without forcing re-renders */}
      <RouteGuard
        path={ROUTES.REGION_ADMIN_DASHBOARD}
        component={RegionUsers}
        permissions={['regionalAdmin', 'globalView']}
      />
      <RouteGuard
        path={ROUTES.GLOBAL_ADMIN_DASHBOARD}
        component={RegionUsers}
        permissions={['regionalAdmin', 'globalView']}
      />
      <RouteGuard
        path={ROUTES.GLOBAL_VIEW_DASHBOARD}
        component={RegionUsers}
        permissions={['regionalAdmin', 'globalView']}
      />
    </Switch>
  );
};
