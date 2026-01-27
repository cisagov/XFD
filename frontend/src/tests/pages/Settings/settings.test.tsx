import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Settings from '../../../pages/Settings';
import { useAuthContext } from 'context';

vi.mock('context', () => ({
  useAuthContext: vi.fn()
}));

vi.mock('@trussworks/react-uswds', () => ({
  Button: ({ children, onClick, type }: any) => (
    <button type={type} onClick={onClick}>
      {children}
    </button>
  )
}));

describe('Settings Component', () => {
  const mockLogout = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders user information correctly when a user is logged in', () => {
    const mockUser = {
      full_name: 'John Doe',
      email: 'john@example.com',
      region_id: 'Region 1',
      roles: [
        { approved: true, organization: { name: 'CISA' } },
        { approved: true, organization: { name: 'FEMA' } },
        { approved: false, organization: { name: 'Hidden Org' } }
      ]
    };

    (useAuthContext as any).mockReturnValue({
      logout: mockLogout,
      user: mockUser
    });

    render(<Settings />);

    expect(screen.getByText('My Account')).toBeInTheDocument();
    expect(screen.getByText(/Name: John Doe/i)).toBeInTheDocument();
    expect(screen.getByText(/Email: john@example.com/i)).toBeInTheDocument();
    expect(screen.getByText(/Member of: CISA, FEMA/i)).toBeInTheDocument();
    expect(screen.getByText(/Region: Region 1/i)).toBeInTheDocument();
  });

  it('displays "None" for region if user has no region_id', () => {
    (useAuthContext as any).mockReturnValue({
      logout: mockLogout,
      user: { full_name: 'Jane Doe', region_id: null }
    });

    render(<Settings />);
    expect(screen.getByText(/Region: None/i)).toBeInTheDocument();
  });

  it('handles user with no roles or unapproved roles gracefully', () => {
    (useAuthContext as any).mockReturnValue({
      logout: mockLogout,
      user: { full_name: 'Jane Doe', roles: [] }
    });

    render(<Settings />);
    expect(screen.getByText(/Member of:$/i)).toBeInTheDocument();
  });

  it('calls the logout function when the button is clicked', () => {
    (useAuthContext as any).mockReturnValue({
      logout: mockLogout,
      user: { full_name: 'John Doe' }
    });

    render(<Settings />);

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    fireEvent.click(logoutButton);

    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

  it('renders labels correctly even if user object is null', () => {
    (useAuthContext as any).mockReturnValue({
      logout: mockLogout,
      user: null
    });

    render(<Settings />);

    expect(screen.getByText(/Name:$/i)).toBeInTheDocument();
    expect(screen.getByText(/Email:$/i)).toBeInTheDocument();
    expect(screen.getByText(/Region: None/i)).toBeInTheDocument();
  });
});
