import React from 'react';
import { render, screen } from 'test-utils';
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { useAuthContext } from '@/context';
import { authCtx } from '@/test-utils/authCtx';
import { Logs } from '../../../components/Logs/Logs';
import {
  regionalAdminUser,
  globalViewUser,
  globalAdminUser,
  testUser
} from '@/test-utils';
import { formatTimestamp } from '@/components/Logs/Logs';

//Mock hooks
vi.mock('@/context/AuthContext');

const sampleLogs = {
  count: 1,
  result: [
    {
      id: 1,
      event_type: 'USER ASSIGNED',
      created_at: '2023-10-01T12:00:00Z',
      result: 'success',
      payload: {
        user_performed_assignment: {
          full_name: 'Test Admin',
          email: 'admin@example.com'
        },
        user: {
          full_name: 'Test User',
          email: 'testuser@example.com',
          user_type: 'standard'
        },
        organization: {
          name: 'Test Org'
        },
        state: 'Florida'
      }
    }
  ]
};

describe('Logs Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    //Logs is only accessible to Global Admins
    const globalAdminAuthCtx = {
      ...authCtx,
      user: globalAdminUser,
      apiPost: vi.fn().mockResolvedValue(sampleLogs)
    };
    vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);
  });
  describe('Renders Logs Page and Columns', () => {
    it('renders Logs page', async () => {
      render(<Logs />);

      const grid = await screen.findByRole('grid');
      expect(grid).toBeInTheDocument();
    });

    it('renders Event column', async () => {
      render(<Logs />);

      const eventColumn = await screen.findByText('Event');
      expect(eventColumn).toBeInTheDocument();
    });

    it('renders Acting User Name column', async () => {
      render(<Logs />);

      const actingUserNameColumn = await screen.findByText('Acting User Name');
      expect(actingUserNameColumn).toBeInTheDocument();
    });

    it('renders Acted-on User Name column', async () => {
      render(<Logs />);

      const actedOnUserNameColumn =
        await screen.findByText('Acted-on User Name');
      expect(actedOnUserNameColumn).toBeInTheDocument();
    });

    it('renders Organization column', async () => {
      render(<Logs />);

      const organizationColumn = await screen.findByText('Organization');
      expect(organizationColumn).toBeInTheDocument();
    });

    it('renders User Type column', async () => {
      render(<Logs />);

      const userTypeColumn = await screen.findByText('User Type');
      expect(userTypeColumn).toBeInTheDocument();
    });

    it('renders Timestamp column', async () => {
      render(<Logs />);

      const timestampColumn = await screen.findByText('Timestamp');
      expect(timestampColumn).toBeInTheDocument();
    });

    it('renders Result column', async () => {
      render(<Logs />);

      const resultColumn = await screen.findByText('Result');
      expect(resultColumn).toBeInTheDocument();
    });

    it('renders Payload column', async () => {
      render(<Logs />);

      const payloadColumn = await screen.findByText('Payload');
      expect(payloadColumn).toBeInTheDocument();
    });
  });

  describe('renders Logs data', async () => {
    it('renders Event data', async () => {
      render(<Logs />);

      const eventRow = await screen.findByText('USER ASSIGNED');
      expect(eventRow).toBeInTheDocument();
    });

    it('renders Acting User Name data', async () => {
      render(<Logs />);

      const actingUserNameRow = await screen.findByText(/Test Admin/i);
      expect(actingUserNameRow).toBeInTheDocument();
    });

    it('renders Acted-on User Name data', async () => {
      render(<Logs />);

      const actedOnUserNameRow = await screen.findByText(/Test User/i);
      expect(actedOnUserNameRow).toBeInTheDocument();
    });

    it('renders Organization data', async () => {
      render(<Logs />);

      const organizationRow = await screen.findByText('Test Org');
      expect(organizationRow).toBeInTheDocument();
    });

    it('renders User Type data', async () => {
      render(<Logs />);

      const userTypeRow = await screen.findByText('standard');
      expect(userTypeRow).toBeInTheDocument();
    });

    it('renders Timestamp data', async () => {
      render(<Logs />);

      const formattedTimestamp = formatTimestamp('2023-10-01T12:00:00Z');
      const timestampRow = await screen.findByText(formattedTimestamp || 'N/A');
      expect(timestampRow).toBeInTheDocument();
    });

    it('renders Result data', async () => {
      render(<Logs />);

      const resultRow = await screen.findByText('success');
      expect(resultRow).toBeInTheDocument();
    });
    it('renders Payload data', async () => {
      render(<Logs />);
      const payloadRow = await screen.findByRole('button', {
        name: /details for log/i
      });
      expect(payloadRow).toBeInTheDocument();
    });
  });
});
