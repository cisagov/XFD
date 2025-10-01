import React from 'react';
import { RouteProps, Route, useHistory } from 'react-router-dom';
import { useAuthContext } from 'context';

interface AuthRedirectRouteProps extends RouteProps {
  unauth?: string | React.ComponentType;
  permissions?: Array<String>;
  component: React.ComponentType;
}

/*
possible states:

- user is authenticated
- user has authenticated but needs to create account
- user has authenticated but needs to sign terms
- user is not authenticated
- user is not authenticated, this is oauth callback (should not be protected)
- user is authenticated, but does not have tha correct permissions for route
*/

export const RouteGuard: React.FC<AuthRedirectRouteProps> = ({
  unauth = '/',
  permissions = [],
  component,
  ...rest
}) => {
  const { token, user, userMustSign, logout } = useAuthContext();
  const history = useHistory();

  if (token && !user) {
    // waiting on user profile
    return null;
  }

  // user has authenticated and registered but needs to create an account
  if (user && !user.isRegistered) {
    history.push('/create-account');
    return null;
  }

  // User must accept terms
  if (user && userMustSign) {
    history.push('/terms');
    return null;
  }

  // Redirect to landing with request sent message for unapproved users
  if (
    user &&
    user.invite_pending &&
    window.location.pathname !== '/' &&
    window.location.pathname !== '/terms' &&
    window.location.pathname !== '/logout'
  ) {
    console.log('User is not approved.');
    history.push('/');
    return null;
  }

  // TODO: Uncomment if we decide to fully block logins during maintenance windows.
  // if (user && user.login_blocked_by_maintenance) {
  //   logout();
  //   return null;
  // }

  if (typeof unauth === 'string' && !user) {
    history.push(unauth);
    return null;
  }

  if (user && permissions && permissions.length > 0) {
    // user is not globalAdmin and invalid user_type permissions
    if (
      user.user_type !== 'globalAdmin' &&
      !permissions.includes(user.user_type)
    ) {
      console.log('User access denied. Logging out!');
      logout();
      history.push('/');
      return null;
    }
  }

  return (
    <Route
      {...rest}
      component={user ? component : (unauth as React.ComponentType)}
    />
  );
};
