// src/components/RouteGuards/RouteGuard.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { RouteGuard } from '@/components';
import { useAuthContext } from 'context';
import { ROUTES } from '@/constants/routes';

// Mock the dependencies
vi.mock('context');
vi.mock('@/utils/logger');

// Mock useHistory
const mockPush = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useHistory: () => ({
      push: mockPush
    })
  };
});

const MockComponent = () => <div data-testid="target">TARGET_COMPONENT</div>;
const MockUnauthComponent = () => (
  <div data-testid="unauth">UNAUTH_COMPONENT</div>
);

describe('RouteGuard', () => {
  const mockLogout = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('allows access if user is authenticated and registered', () => {
    (useAuthContext as any).mockReturnValue({
      user: { isRegistered: true, user_type: 'standard' },
      logout: mockLogout
    });

    render(
      <MemoryRouter initialEntries={['/test']}>
        <RouteGuard path="/test" component={MockComponent} />
      </MemoryRouter>
    );

    expect(screen.getByTestId('target')).toBeInTheDocument();
  });

  it('redirects to /create-account if user is not registered', () => {
    (useAuthContext as any).mockReturnValue({
      user: { isRegistered: false, user_type: 'standard' },
      logout: mockLogout
    });

    render(
      <MemoryRouter initialEntries={['/test']}>
        <RouteGuard path="/test" component={MockComponent} />
      </MemoryRouter>
    );

    expect(mockPush).toHaveBeenCalledWith('/create-account');
    expect(screen.queryByTestId('target')).not.toBeInTheDocument();
  });

  it('redirects to home if user invite is pending', () => {
    vi.stubGlobal('location', { pathname: '/inventory' });

    (useAuthContext as any).mockReturnValue({
      user: {
        isRegistered: true,
        invite_pending: true,
        user_type: 'standard'
      },
      logout: mockLogout
    });

    render(
      <MemoryRouter initialEntries={['/inventory']}>
        <RouteGuard path="/inventory" component={MockComponent} />
      </MemoryRouter>
    );

    expect(mockPush).toHaveBeenCalledWith(ROUTES.HOME);
    vi.unstubAllGlobals();
  });

  it('redirects to unauth path if user is not logged in and unauth is a string', () => {
    (useAuthContext as any).mockReturnValue({
      user: null,
      logout: mockLogout
    });

    render(
      <MemoryRouter initialEntries={['/test']}>
        <RouteGuard path="/test" unauth="/login" component={MockComponent} />
      </MemoryRouter>
    );

    expect(mockPush).toHaveBeenCalledWith('/login');
  });

  it('renders unauth component if user is not logged in and unauth is a component', () => {
    (useAuthContext as any).mockReturnValue({
      user: null,
      logout: mockLogout
    });

    render(
      <MemoryRouter initialEntries={['/test']}>
        <RouteGuard
          path="/test"
          unauth={MockUnauthComponent}
          component={MockComponent}
        />
      </MemoryRouter>
    );

    expect(screen.getByTestId('unauth')).toBeInTheDocument();
  });

  it('logs out and redirects if user lacks correct permissions', () => {
    (useAuthContext as any).mockReturnValue({
      user: { isRegistered: true, user_type: 'standard' },
      logout: mockLogout
    });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <RouteGuard
          path="/admin"
          permissions={['globalAdmin']}
          component={MockComponent}
        />
      </MemoryRouter>
    );

    expect(mockLogout).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith(ROUTES.HOME);
  });

  it('allows access even if permissions do not match if user is globalAdmin', () => {
    (useAuthContext as any).mockReturnValue({
      user: { isRegistered: true, user_type: 'globalAdmin' },
      logout: mockLogout
    });

    render(
      <MemoryRouter initialEntries={['/any-route']}>
        <RouteGuard
          path="/any-route"
          permissions={['standard']}
          component={MockComponent}
        />
      </MemoryRouter>
    );

    expect(screen.getByTestId('target')).toBeInTheDocument();
  });
});
