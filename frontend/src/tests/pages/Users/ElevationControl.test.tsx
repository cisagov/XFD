import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ElevationControl } from '@/pages/Users/ElevationControl';
import { User } from 'types';

describe('ElevationControl Component', () => {
  // Helper to construct baseline mock mock props
  const createMockProps = (overrides = {}) => ({
    confirmGlobalAdminChange: '',
    setConfirmGlobalAdminChange: vi.fn(),
    userRoleChanged: false,
    values: {
      user_type: 'standard',
      email: 'test@example.com'
    } as unknown as User,
    isRoleElevationConfirmed: false,
    setIsRoleElevationConfirmed: vi.fn(),
    userOrg: 'CISA',
    ...overrides
  });

  it('renders nothing if userRoleChanged is false', () => {
    const props = createMockProps({ userRoleChanged: false });
    const { container } = render(<ElevationControl {...props} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing if values.user_type is "standard"', () => {
    const props = createMockProps({
      userRoleChanged: true,
      values: { user_type: 'standard' }
    });
    const { container } = render(<ElevationControl {...props} />);
    expect(container.firstChild).toBeNull();
  });

  describe('Global Admin Elevation Flow', () => {
    it('renders warning alert and textfield with userOrg when elevating to globalAdmin', () => {
      const props = createMockProps({
        userRoleChanged: true,
        values: { user_type: 'globalAdmin', email: 'admin@example.com' },
        userOrg: 'CISA'
      });

      render(<ElevationControl {...props} />);

      // Verify warning message is present and correctly formats email + org combination
      expect(screen.getByRole('alert')).toHaveTextContent(
        'You are attempting to change user admin@example.com - CISA to a Global Administrator'
      );

      // Verify placeholder configuration matches
      expect(
        screen.getByPlaceholderText('Enter Global Administrator to confirm')
      ).toBeInTheDocument();
    });

    it('renders alert without userOrg formatting if userOrg is missing', () => {
      const props = createMockProps({
        userRoleChanged: true,
        values: { user_type: 'globalAdmin', email: 'admin@example.com' },
        userOrg: null
      });

      render(<ElevationControl {...props} />);
      expect(screen.getByRole('alert')).toHaveTextContent(
        'You are attempting to change user admin@example.com to a Global Administrator'
      );
    });

    it('invokes setConfirmGlobalAdminChange whenever typing into the TextField', async () => {
      const setConfirmGlobalAdminChangeMock = vi.fn();
      const props = createMockProps({
        userRoleChanged: true,
        values: { user_type: 'globalAdmin', email: 'admin@example.com' },
        setConfirmGlobalAdminChange: setConfirmGlobalAdminChangeMock
      });

      render(<ElevationControl {...props} />);

      const input = screen.getByPlaceholderText(
        'Enter Global Administrator to confirm'
      );
      await userEvent.type(input, 'G');

      expect(setConfirmGlobalAdminChangeMock).toHaveBeenCalledWith('G');
    });
  });

  describe('Regional Admin / Global View Elevation Flow', () => {
    it('renders target message and active confirmation button when unconfirmed', async () => {
      const setIsRoleElevationConfirmedMock = vi.fn();
      const props = createMockProps({
        userRoleChanged: true,
        values: { user_type: 'regionalAdmin' },
        isRoleElevationConfirmed: false,
        setIsRoleElevationConfirmed: setIsRoleElevationConfirmedMock
      });

      render(<ElevationControl {...props} />);

      expect(screen.getByRole('alert')).toHaveTextContent(
        'You are attempting to change this user to Regional Administrator.'
      );

      const confirmButton = screen.getByRole('button', {
        name: 'Confirm Privilege Elevation'
      });
      expect(confirmButton).toBeEnabled();

      await userEvent.click(confirmButton);
      expect(setIsRoleElevationConfirmedMock).toHaveBeenCalledWith(true);
    });

    it('renders globalView message options cleanly', () => {
      const props = createMockProps({
        userRoleChanged: true,
        values: { user_type: 'globalView' }
      });

      render(<ElevationControl {...props} />);
      expect(screen.getByRole('alert')).toHaveTextContent(
        'You are attempting to change this user to Global View.'
      );
    });

    it('disables confirmation button and switches label text when isRoleElevationConfirmed is true', () => {
      const props = createMockProps({
        userRoleChanged: true,
        values: { user_type: 'regionalAdmin' },
        isRoleElevationConfirmed: true
      });

      render(<ElevationControl {...props} />);

      const confirmedButton = screen.getByRole('button', {
        name: 'Confirmed Privilege Elevation'
      });
      expect(confirmedButton).toBeDisabled();
    });
  });
});
