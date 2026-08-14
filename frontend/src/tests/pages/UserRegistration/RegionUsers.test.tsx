import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { waitFor, act } from '@testing-library/react';
import { render } from '@/test-utils/test-utils';
import { RegionUsers } from '@/pages/UserRegistration/RegionUsers';
import { ENDPOINTS } from '@/constants/endpoints';

const REGISTRATION_USERS_REFRESH_INTERVAL_MS = 30_000;

vi.mock('@mui/x-data-grid', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mui/x-data-grid')>();
  return {
    ...actual,
    DataGrid: ({
      rows = [],
      columns = []
    }: {
      rows?: Array<Record<string, unknown>>;
      columns?: Array<{
        field?: string;
        renderCell?: (params: {
          row: Record<string, unknown>;
        }) => React.ReactNode;
      }>;
    }) => (
      <div data-testid="data-grid">
        {rows.map((row) => {
          const statusCol = columns.find((col) => col.field === 'status');
          if (!statusCol?.renderCell) {
            return null;
          }
          return (
            <div key={String(row.id)} data-testid={`row-${row.id}`}>
              {statusCol.renderCell({ row })}
            </div>
          );
        })}
      </div>
    ),
    useGridApiRef: () => ({ current: { updateRows: vi.fn() } }),
    GridToolbar: () => null
  };
});

vi.mock('@components/Metrics/Widgets/ExportCustomerMetricsButton', () => ({
  ExportCustomerMetricsButton: () => null
}));

vi.mock('hooks/useUserLevel', () => ({
  useUserLevel: () => ({ formattedUserType: 'standard' })
}));

vi.mock('@/utils/transformTableData', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@/utils/transformTableData')>();
  return {
    ...actual,
    transformUserData: (rows: unknown[]) => rows
  };
});

vi.mock('@/pages/UserRegistration/OrganizationSelector', () => ({
  OrganizationSelector: ({ onSelectionChange }: any) => (
    <div data-testid="organization-selector">
      <button
        onClick={() => onSelectionChange({ id: 'org-1', name: 'Virginia Org' })}
      >
        Select organization
      </button>
    </div>
  )
}));

const getUsersURL = `${ENDPOINTS.USERS_V2}?invite_pending=`;

describe('RegionUsers', () => {
  const apiGet = vi.fn();
  const apiPost = vi.fn();
  const apiDelete = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    apiGet.mockResolvedValue([]);
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('refetches pending and current users on the refresh interval', async () => {
    render(<RegionUsers />, {
      authContext: { apiGet, apiPost, apiDelete }
    });

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith(`${getUsersURL}true`);
      expect(apiGet).toHaveBeenCalledWith(`${getUsersURL}false`);
    });

    const callsAfterMount = apiGet.mock.calls.length;
    expect(callsAfterMount).toBe(2);

    await act(async () => {
      vi.advanceTimersByTime(REGISTRATION_USERS_REFRESH_INTERVAL_MS);
    });

    await waitFor(() => {
      expect(apiGet.mock.calls.length).toBeGreaterThan(callsAfterMount);
    });

    const pollCalls = apiGet.mock.calls.slice(callsAfterMount);
    expect(pollCalls).toContainEqual([`${getUsersURL}true`]);
    expect(pollCalls).toContainEqual([`${getUsersURL}false`]);
  });

  it('does not poll while the approve org dialog is open', async () => {
    const pendingUser = {
      id: 'user-1',
      full_name: 'Pending User',
      email: 'pending@example.com',
      region_id: 'region-1',
      roles: []
    };

    apiGet.mockImplementation((url: string) => {
      if (url === `${getUsersURL}true`) {
        return Promise.resolve([pendingUser]);
      }
      return Promise.resolve([]);
    });

    const { getByRole } = render(<RegionUsers />, {
      authContext: { apiGet, apiPost, apiDelete }
    });

    await waitFor(() => {
      expect(
        getByRole('button', { name: /Approve User: Pending User/i })
      ).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(apiGet.mock.calls.length).toBe(2);
    });

    getByRole('button', { name: /Approve User: Pending User/i }).click();

    await waitFor(() => {
      expect(
        document.querySelector('[data-testid="organization-selector"]')
      ).toBeInTheDocument();
    });

    const callsWithDialogOpen = apiGet.mock.calls.length;

    await act(async () => {
      vi.advanceTimersByTime(REGISTRATION_USERS_REFRESH_INTERVAL_MS);
    });

    expect(apiGet.mock.calls.length).toBe(callsWithDialogOpen);
  });

  it('completes approval with one request containing state and organization', async () => {
    const pendingUser = {
      id: 'user-1',
      full_name: 'Pending User',
      email: 'pending@example.com',
      state: 'Virginia',
      region_id: '3',
      user_type: 'standard',
      roles: []
    };
    apiGet.mockImplementation((url: string) =>
      Promise.resolve(url === `${getUsersURL}true` ? [pendingUser] : [])
    );
    apiPost.mockResolvedValue({
      status_code: 200,
      body: 'User registration approved.',
      email_sent: false
    });

    const { getByRole } = render(<RegionUsers />, {
      authContext: { apiGet, apiPost, apiDelete }
    });

    await waitFor(() => {
      expect(
        getByRole('button', { name: /Approve User: Pending User/i })
      ).toBeInTheDocument();
    });

    getByRole('button', { name: /Approve User: Pending User/i }).click();
    await waitFor(() => {
      expect(
        getByRole('button', { name: /Select organization/i })
      ).toBeInTheDocument();
    });
    getByRole('button', { name: /Select organization/i }).click();
    await waitFor(() => {
      expect(getByRole('button', { name: 'Confirm' })).toBeEnabled();
    });
    getByRole('button', { name: 'Confirm' }).click();

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(
        ENDPOINTS.USERS_REGISTER_APPROVE.replace('{user_id}', 'user-1'),
        {
          body: {
            state: 'Virginia',
            organization_id: 'org-1'
          }
        }
      );
    });

    await waitFor(() => {
      expect(getByRole('dialog', { name: /Success/i })).toHaveTextContent(
        'The approval email could not be sent. Check the network tab for details.'
      );
    });
  });
});
