import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from 'test-utils';
import userEvent from '@testing-library/user-event';
import type { Organization } from 'types';
import UserForm from '@/pages/Users/UserForm';

// ---- mock handles ----
const mockUseAuthContext = vi.fn();
const mockUseOrganizationsByRegion = vi.fn();
const mockUpdateUser = vi.fn();
const mockAddUserToOrganization = vi.fn();
const mockRemoveUserFromOrganization = vi.fn();

vi.mock('context', async () => {
  const actual = await vi.importActual<any>('context');

  return {
    ...actual,
    useAuthContext: () => mockUseAuthContext()
  };
});

vi.mock('@/hooks/useOrganizationsByRegion', () => ({
  useOrganizationsByRegion: (...args: unknown[]) =>
    mockUseOrganizationsByRegion(...args)
}));

vi.mock('@/hooks/useUpdateUser', () => ({
  useUpdateUser: () => ({ updateUser: mockUpdateUser })
}));

vi.mock('@/hooks/useAddUserToOrganization', () => ({
  useAddUserToOrganization: () => ({
    addUserToOrganization: mockAddUserToOrganization
  })
}));

vi.mock('@/hooks/useRemoveUserFromOrganization', () => ({
  useRemoveUserFromOrganization: () => ({
    removeUserFromOrganization: mockRemoveUserFromOrganization
  })
}));

vi.mock('components/Dialog/AnimatedConfirmDialog', () => ({
  __esModule: true,
  default: ({
    isOpen,
    onConfirm,
    onCancel,
    title,
    content,
    disabled
  }: {
    isOpen: boolean;
    onConfirm: () => void;
    onCancel: () => void;
    title: React.ReactNode;
    content: React.ReactNode;
    disabled?: boolean;
  }) =>
    isOpen ? (
      <div
        data-testid="user-form-dialog"
        data-disabled={disabled ? 'true' : 'false'}
      >
        <h2>{title}</h2>
        <div data-testid="user-form-dialog-content">{content}</div>
        <button
          data-testid="user-form-confirm"
          type="button"
          onClick={onConfirm}
        >
          Confirm
        </button>
        <button data-testid="user-form-cancel" type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    ) : null
}));

// -------------------- Helpers --------------------

const makeOrganization = (
  overrides: Partial<Organization> = {}
): Organization => ({
  id: 'default-org-id',
  name: 'Default Org',
  acronym: 'DEF',
  root_domains: [],
  ip_blocks: [],
  is_passive: false,
  pending_domains: [],
  type: '' as any,
  ...overrides
});

// -------------------- Shared test data --------------------

const baseApiErrorStates = {
  getUsersError: '',
  getAddUserError: '',
  getDeleteError: '',
  getUpdateUserError: '',
  getOrgsError: ''
};

const baseValues: any = {
  id: 1,
  first_name: 'Jane',
  last_name: 'Doe',
  email: 'jane@example.com',
  user_type: 'standard',
  state: 'VA',
  region_id: '1',
  org_id: 'org-1',
  org_name: 'Org One',
  originalOrgId: 'org-1',
  originalRoleId: 'role-1'
};

const baseUsers: any[] = [
  {
    id: 1,
    first_name: 'Jane',
    last_name: 'Doe',
    email: 'jane@example.com',
    user_type: 'standard',
    full_name: 'Jane Doe',
    roles: [
      {
        organization: { name: 'Org One' }
      }
    ],
    state: 'VA',
    region_id: '1',
    org_id: 'org-1'
  }
];

// -------------------- Tests --------------------

describe('UserForm', () => {
  const mockSetUsers = vi.fn();
  const mockSetValues = vi.fn();
  const mockSetEditUserDialogOpen = vi.fn();
  const mockSetApiErrorStates = vi.fn();
  const mockSetInfoDialogOpen = vi.fn();
  const mockSetInfoDialogContent = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    mockUseAuthContext.mockReturnValue({
      user: {
        id: 'auth-user-id',
        user_type: 'globalAdmin'
      }
    } as any);

    mockUseOrganizationsByRegion.mockReturnValue({
      organizations: [
        makeOrganization({
          id: 'org-1',
          name: 'Org One',
          acronym: 'ONE'
        })
      ],
      isLoading: false,
      errorMessage: '',
      refetch: vi.fn()
    });

    mockUpdateUser.mockResolvedValue(undefined);
    mockAddUserToOrganization.mockResolvedValue(undefined);
    mockRemoveUserFromOrganization.mockResolvedValue(undefined);
  });

  /**
   * Verifies a successful submit calls updateUser with the correct payload,
   * does not change org membership when org_id is unchanged, updates the users
   * list, closes the dialog, and shows a success message.
   */
  it('submits successfully and updates users list', async () => {
    const user = userEvent.setup();

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={baseValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const confirmButton = await screen.findByTestId('user-form-confirm');
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledTimes(1);
    });

    const [calledId, calledBody] = mockUpdateUser.mock.calls[0];

    expect(calledId).toBe(1);
    expect(calledBody).toMatchObject({
      first_name: 'Jane',
      last_name: 'Doe',
      state: 'VA',
      region_id: '1'
    });

    expect(mockRemoveUserFromOrganization).not.toHaveBeenCalled();
    expect(mockAddUserToOrganization).not.toHaveBeenCalled();

    expect(mockSetUsers).toHaveBeenCalledTimes(1);
    expect(mockSetEditUserDialogOpen).toHaveBeenCalledWith(false);
    expect(mockSetInfoDialogContent).toHaveBeenCalledWith(
      'This user has been successfully updated.'
    );
    expect(mockSetInfoDialogOpen).toHaveBeenCalledWith(true);
  });

  /**
   * Verifies a failed update surfaces the error to UI state by calling
   * setApiErrorStates and showing a failure message to the user.
   */
  it('handles updateUser error and sets error state', async () => {
    const user = userEvent.setup();

    const error = Object.assign(new Error('Update failed'), {
      response: { data: { detail: 'Bad things happened' } }
    });

    mockUpdateUser.mockRejectedValueOnce(error);

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={baseValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const confirmButton = await screen.findByTestId('user-form-confirm');
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledTimes(1);
    });

    expect(mockSetApiErrorStates).toHaveBeenCalled();
    expect(mockSetInfoDialogContent).toHaveBeenCalledWith(
      'This user has not been updated. Check the console log for more details.'
    );
    expect(mockSetInfoDialogOpen).toHaveBeenCalledWith(true);
  });

  /**
   * Verifies when org_id changes in edit mode, the form removes the user from
   * the original organization/role and then adds them to the new organization.
   */
  it('removes and re-adds user to organization when org_id changes', async () => {
    const user = userEvent.setup();

    const changedValues = {
      ...baseValues,
      org_id: 'org-2',
      org_name: 'Org Two',
      originalOrgId: 'org-1',
      originalRoleId: 'role-1'
    };

    mockUseOrganizationsByRegion.mockReturnValue({
      organizations: [
        makeOrganization({
          id: 'org-1',
          name: 'Org One',
          acronym: 'ONE'
        }),
        makeOrganization({
          id: 'org-2',
          name: 'Org Two',
          acronym: 'TWO'
        })
      ],
      isLoading: false,
      errorMessage: '',
      refetch: vi.fn()
    });

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={changedValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const confirmButton = await screen.findByTestId('user-form-confirm');
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledTimes(1);
    });

    expect(mockRemoveUserFromOrganization).toHaveBeenCalledWith(
      'org-1',
      'role-1'
    );
    expect(mockAddUserToOrganization).toHaveBeenCalledWith('org-2', 1, 'user');
  });

  /**
   * Verifies the email field is locked in edit mode to prevent changing
   * an existing user’s email address.
   */
  it('keeps email disabled in edit mode', () => {
    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={baseValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const emailInput = screen.getByPlaceholderText('Enter an Email');
    expect(emailInput).toBeDisabled();
  });

  /**
   * Verifies first name validation rejects numeric input and shows the
   * expected helper text.
   */
  it('shows validation error for invalid first name', async () => {
    const user = userEvent.setup();

    const valuesWithInvalidFirstName = {
      ...baseValues,
      first_name: '1234'
    };

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={valuesWithInvalidFirstName}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const confirmButton = await screen.findByTestId('user-form-confirm');
    await user.click(confirmButton);

    expect(
      await screen.findByText(
        'First Name is required and cannot contain numbers'
      )
    ).toBeInTheDocument();
  });

  /**
   * Verifies the organization field is required and shows a helper error
   * when org_id is empty.
   */
  it('shows organization required error helper when org_id is empty', () => {
    const valuesWithoutOrg = {
      ...baseValues,
      org_id: '',
      org_name: ''
    };

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={valuesWithoutOrg}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    expect(screen.getByText('Organization is required')).toBeInTheDocument();
  });

  /**
   * Verifies the update error alert renders when getUpdateUserError is present,
   * so backend/update failures are visible to the user.
   */
  it('renders update error alert when getUpdateUserError is present', () => {
    const apiErrorStatesWithUpdateError = {
      ...baseApiErrorStates,
      getUpdateUserError: 'Something went wrong updating user'
    };

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={baseValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={apiErrorStatesWithUpdateError}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    expect(
      screen.getByText(/Error updating user in the database:/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Something went wrong updating user/i)
    ).toBeInTheDocument();
  });

  /**
   * Verifies org fetch failures propagate into apiErrorStates.getOrgsError
   * via setApiErrorStates so the UI can show org-loading errors.
   */
  it('updates getOrgsError via setApiErrorStates when org fetch fails', async () => {
    const errorMessage = 'Failed to fetch orgs. Bad request';

    mockUseOrganizationsByRegion.mockReturnValue({
      organizations: [],
      isLoading: false,
      errorMessage,
      refetch: vi.fn()
    });

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={baseValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    await waitFor(() => {
      expect(mockSetApiErrorStates).toHaveBeenCalled();
    });

    const updater = mockSetApiErrorStates.mock.calls[0][0] as (
      previous: typeof baseApiErrorStates
    ) => typeof baseApiErrorStates;

    expect(typeof updater).toBe('function');

    const updatedState = updater(baseApiErrorStates);
    expect(updatedState.getOrgsError).toBe(errorMessage);
  });

  /**
   * Verifies create mode starts with empty inputs for new user creation.
   */
  it('in create mode initializes fields as empty', () => {
    const createModeValues = {
      ...baseValues,
      id: undefined,
      first_name: '',
      last_name: '',
      email: '',
      org_id: '',
      org_name: '',
      originalOrgId: '',
      originalRoleId: ''
    };

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={createModeValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const firstNameInput = screen.getByPlaceholderText('Enter a First Name');
    const lastNameInput = screen.getByPlaceholderText('Enter a Last Name');
    const emailInput = screen.getByPlaceholderText('Enter an Email');

    expect(firstNameInput).toHaveValue('');
    expect(lastNameInput).toHaveValue('');
    expect(emailInput).toHaveValue('');
  });

  /**
   * Verifies edit mode pre-populates the form with the selected user’s
   * existing data.
   */
  it('in edit mode pre-populates all existing user data', () => {
    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={baseValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const firstNameInput = screen.getByPlaceholderText('Enter a First Name');
    const lastNameInput = screen.getByPlaceholderText('Enter a Last Name');
    const emailInput = screen.getByPlaceholderText('Enter an Email');

    expect(firstNameInput).toHaveValue('Jane');
    expect(lastNameInput).toHaveValue('Doe');
    expect(emailInput).toHaveValue('jane@example.com');
  });

  /**
   * Verifies create-mode email validation rejects an invalid email format,
   * shows the helper text, and prevents submission.
   */
  it('shows validation error for invalid email format in create mode', async () => {
    const user = userEvent.setup();

    const valuesWithInvalidEmail = {
      ...baseValues,
      id: undefined,
      email: 'not-a-valid-email',
      org_id: 'org-1',
      originalOrgId: '',
      originalRoleId: ''
    };

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={valuesWithInvalidEmail}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const confirmButton = await screen.findByTestId('user-form-confirm');
    await user.click(confirmButton);

    expect(
      await screen.findByText(
        'Email is required and must be in the correct format'
      )
    ).toBeInTheDocument();

    expect(mockUpdateUser).not.toHaveBeenCalled();
  });

  /**
   * Verifies the confirm dialog is disabled during an in-flight submission
   * to prevent duplicate requests, and re-enables/closes when finished.
   */
  it('disables the dialog while submission is in progress', async () => {
    const user = userEvent.setup();

    let resolveUpdate: () => void;
    const updatePromise = new Promise<void>((resolve) => {
      resolveUpdate = resolve;
    });

    mockUpdateUser.mockReturnValueOnce(
      updatePromise as unknown as Promise<void>
    );

    render(
      <UserForm
        users={baseUsers}
        setUsers={mockSetUsers}
        values={baseValues}
        setValues={mockSetValues}
        editUserDialogOpen={true}
        setEditUserDialogOpen={mockSetEditUserDialogOpen}
        apiErrorStates={baseApiErrorStates}
        setApiErrorStates={mockSetApiErrorStates}
        setInfoDialogOpen={mockSetInfoDialogOpen}
        setInfoDialogContent={mockSetInfoDialogContent}
      />
    );

    const confirmButton = await screen.findByTestId('user-form-confirm');
    await user.click(confirmButton);

    const dialog = await screen.findByTestId('user-form-dialog');
    expect(dialog).toHaveAttribute('data-disabled', 'true');

    resolveUpdate!();

    await waitFor(() => {
      expect(mockSetEditUserDialogOpen).toHaveBeenCalledWith(false);
    });
  });
});
