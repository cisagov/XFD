import React from 'react';
import { render, screen, testUser } from 'test-utils';
import { beforeEach, describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import type { AuthUser } from '@/context';
import OrganizationSelector from '@/pages/UserRegistration/OrganizationSelector';
import type { OrganizationSelectorProps } from '@/pages/UserRegistration/OrganizationSelector';
import { ENDPOINTS } from '@/constants/endpoints';
import { mockOrganizations as organizations } from '@/test-utils/searchOrg';
import { authCtx } from '@/test-utils/authCtx';

describe('OrganizationSelector', () => {
  const apiGetMock = vi.fn().mockResolvedValue(organizations);

  beforeEach(() => {
    apiGetMock.mockClear();
  });

  const renderComponent = (props?: Partial<OrganizationSelectorProps>) => {
    const onSelectionChange = vi.fn();
    const selectUserMock = vi.fn();
    render(
      <OrganizationSelector
        regionId="123"
        onSelectionChange={onSelectionChange}
        selectedUser={testUser}
        pendingUsers={[testUser]}
        selectUser={selectUserMock}
        formattedUserType="Standard User"
        getUpdateError=""
        {...props}
      />,
      {
        authContext: {
          apiGet: apiGetMock,
          currentOrganization: null,
          user: testUser as unknown as AuthUser
        }
      }
    );
    return { onSelectionChange };
  };

  it('fetches and renders organizations', async () => {
    apiGetMock.mockResolvedValueOnce(organizations);

    renderComponent();

    const grid = await screen.findByRole('grid');
    expect(grid).toBeInTheDocument();

    expect(await screen.findByText('Organization 1')).toBeInTheDocument();
    expect(await screen.findByText('Organization 2')).toBeInTheDocument();

    const rows = await screen.findAllByRole('row');
    // header row + 2 data rows
    expect(rows).toHaveLength(organizations.length + 1);

    expect(apiGetMock).toHaveBeenCalledWith(
      ENDPOINTS.ORGANIZATIONS_REGION.replace('{region_id}', '123')
    );
  });

  it('renders error when regionId is missing', async () => {
    render(
      <OrganizationSelector
        regionId={null}
        onSelectionChange={vi.fn()}
        selectedUser={testUser}
        pendingUsers={[testUser]}
        selectUser={vi.fn()}
        formattedUserType="Standard User"
        getUpdateError=""
      />,
      {
        authContext: {
          ...authCtx,
          apiGet: apiGetMock,
          user: testUser as unknown as AuthUser
        }
      }
    );

    expect(
      await screen.findByText(/this user has no region assigned/i)
    ).toBeInTheDocument();
  });

  it('renders API error state', async () => {
    apiGetMock.mockRejectedValueOnce(new Error('API failure'));

    renderComponent();

    expect(
      await screen.findByText(/error retrieving organizations/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/api failure/i)).toBeInTheDocument();
  });

  it('shows info alert when an organization is selected', async () => {
    apiGetMock.mockResolvedValueOnce(organizations);
    renderComponent();

    const user = userEvent.setup();

    expect(await screen.findByText('Organization 1')).toBeInTheDocument();

    const checkboxes = await screen.findAllByRole('checkbox');

    await user.click(checkboxes[1]);

    expect(
      await screen.findByText(
        /will become a member of the selected organization/i
      )
    ).toBeInTheDocument();
  });

  it('does not request elevation confirmation for a preselected elevated user type', async () => {
    const elevatedUser = { ...testUser, user_type: 'globalView' as const };

    renderComponent({ selectedUser: elevatedUser, pendingUsers: [] });

    expect(
      screen.queryByText(/you are attempting to change this user/i)
    ).not.toBeInTheDocument();
  });

  it('respects initialOrgId selection', async () => {
    apiGetMock.mockResolvedValueOnce(organizations);

    renderComponent({ initialOrgId: 'org-2' });

    expect(
      await screen.findByText(
        /will become a member of the selected organization/i
      )
    ).toBeInTheDocument();
  });
});
