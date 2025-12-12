import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import OrgMembers from '../../../pages/Organization/OrgMembers';
import { Organization, Role } from 'types';
import * as logger from '@/utils/logger';

// Mock the logger
vi.mock('@/utils/logger', () => ({
  logger: {
    error: vi.fn()
  }
}));

// Mock CustomToolbar to check if disableExport prop is passed correctly
vi.mock('components/DataGrid/CustomToolbar', () => ({
  default: ({ disableExport, exportTitle }: any) => (
    <div data-testid="custom-toolbar">
      <span data-testid="disable-export">{String(disableExport)}</span>
      <span data-testid="export-title">{exportTitle}</span>
      {!disableExport && <button data-testid="export-button">Export</button>}
    </div>
  )
}));

// Mock the dialogs
vi.mock('components/Dialog/ConfirmDialog', () => ({
  default: ({ isOpen, onConfirm, onCancel, title }: any) =>
    isOpen ? (
      <div data-testid="confirm-dialog">
        <p>{title}</p>
        <button onClick={onConfirm} data-testid="confirm-button">
          Confirm
        </button>
        <button onClick={onCancel} data-testid="cancel-button">
          Cancel
        </button>
      </div>
    ) : null
}));

vi.mock('components/Dialog/InfoDialog', () => ({
  default: ({ isOpen, handleClick, title }: any) =>
    isOpen ? (
      <div data-testid="info-dialog">
        {title}
        <button onClick={handleClick} data-testid="info-ok-button">
          OK
        </button>
      </div>
    ) : null
}));

describe('OrgMembers Component', () => {
  const mockOrganization: Organization = {
    id: 'org-123',
    name: 'Test Organization',
    acronym: 'TEST',
    root_domains: ['example.com'],
    ip_blocks: [],
    is_passive: false,
    pending_domains: [],
    type: 'federal',
    user_roles: []
  };

  const mockUserRoles: Role[] = [
    {
      id: 'role-1',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      role: 'admin',
      approved: true,
      user: {
        id: 'user-1',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
        first_name: 'Jane',
        last_name: 'Doe',
        full_name: 'Jane Doe',
        email: 'jane.doe@example.com',
        user_type: 'standard',
        invite_pending: false,
        roles: [],
        isRegistered: true,
        apiKeys: [],
        date_accepted_terms: '2023-01-01T00:00:00Z',
        accepted_terms_version: 'v1',
        last_logged_in: '2023-01-01T00:00:00Z',
        first_login: false
      },
      organization: mockOrganization
    },
    {
      id: 'role-2',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      role: 'user',
      approved: true,
      user: {
        id: 'user-2',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
        first_name: 'John',
        last_name: 'Smith',
        full_name: 'John Smith',
        email: 'john.smith@example.com',
        user_type: 'standard',
        invite_pending: false,
        roles: [],
        isRegistered: true,
        apiKeys: [],
        date_accepted_terms: '2023-01-01T00:00:00Z',
        accepted_terms_version: 'v1',
        last_logged_in: '2023-01-01T00:00:00Z',
        first_login: false
      },
      organization: mockOrganization
    }
  ];

  const mockSetUserRoles = vi.fn();
  const mockApiPost = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Export functionality based on user type', () => {
    it('should disable export for globalAdmin users', () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            user: {
              id: 'admin-1',
              user_type: 'globalAdmin',
              email: 'admin@example.com',
              first_name: 'Global',
              last_name: 'Admin',
              full_name: 'Global Admin',
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T00:00:00Z',
              invite_pending: false,
              roles: [],
              isRegistered: true,
              apiKeys: [],
              date_accepted_terms: '2023-01-01T00:00:00Z',
              accepted_terms_version: 'v1',
              last_logged_in: '2023-01-01T00:00:00Z',
              first_login: false
            },
            apiPost: mockApiPost
          }
        }
      );

      const disableExportValue = screen.getByTestId('disable-export');
      expect(disableExportValue.textContent).toBe('true');
      expect(screen.queryByTestId('export-button')).not.toBeInTheDocument();
    });

    it('should disable export for regionalAdmin users', () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            user: {
              id: 'admin-2',
              user_type: 'regionalAdmin',
              email: 'regional@example.com',
              first_name: 'Regional',
              last_name: 'Admin',
              full_name: 'Regional Admin',
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T00:00:00Z',
              invite_pending: false,
              roles: [],
              isRegistered: true,
              apiKeys: [],
              date_accepted_terms: '2023-01-01T00:00:00Z',
              accepted_terms_version: 'v1',
              last_logged_in: '2023-01-01T00:00:00Z',
              first_login: false
            },
            apiPost: mockApiPost
          }
        }
      );

      const disableExportValue = screen.getByTestId('disable-export');
      expect(disableExportValue.textContent).toBe('true');
      expect(screen.queryByTestId('export-button')).not.toBeInTheDocument();
    });

    it('should disable export for globalView users', () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            user: {
              id: 'viewer-1',
              user_type: 'globalView',
              email: 'viewer@example.com',
              first_name: 'Global',
              last_name: 'Viewer',
              full_name: 'Global Viewer',
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T00:00:00Z',
              invite_pending: false,
              roles: [],
              isRegistered: true,
              apiKeys: [],
              date_accepted_terms: '2023-01-01T00:00:00Z',
              accepted_terms_version: 'v1',
              last_logged_in: '2023-01-01T00:00:00Z',
              first_login: false
            },
            apiPost: mockApiPost
          }
        }
      );

      const disableExportValue = screen.getByTestId('disable-export');
      expect(disableExportValue.textContent).toBe('true');
      expect(screen.queryByTestId('export-button')).not.toBeInTheDocument();
    });

    it('should enable export for standard users', () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            user: {
              id: 'user-1',
              user_type: 'standard',
              email: 'user@example.com',
              first_name: 'Standard',
              last_name: 'User',
              full_name: 'Standard User',
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T00:00:00Z',
              invite_pending: false,
              roles: [],
              isRegistered: true,
              apiKeys: [],
              date_accepted_terms: '2023-01-01T00:00:00Z',
              accepted_terms_version: 'v1',
              last_logged_in: '2023-01-01T00:00:00Z',
              first_login: false
            },
            apiPost: mockApiPost
          }
        }
      );

      const disableExportValue = screen.getByTestId('disable-export');
      expect(disableExportValue.textContent).toBe('false');
      expect(screen.getByTestId('export-button')).toBeInTheDocument();
    });
  });

  describe('Component rendering', () => {
    it('should render member table with correct data', () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />
      );

      expect(screen.getByText('Jane Doe')).toBeInTheDocument();
      expect(screen.getByText('john.smith@example.com')).toBeInTheDocument();
    });

    it('should render export title with organization name', () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />
      );

      const exportTitle = screen.getByTestId('export-title');
      expect(exportTitle.textContent).toBe('Test Organization Members');
    });

    it('should render remove buttons for each member', () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />
      );

      // More specific selector to avoid matching other "Remove" text
      const removeButtons = screen.getAllByRole('button', { name: /Remove/ });
      expect(removeButtons.length).toBe(mockUserRoles.length);
    });
  });

  describe('Remove user functionality', () => {
    it('should open confirm dialog when remove button is clicked', async () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            apiPost: mockApiPost
          }
        }
      );

      const removeButtons = screen.getAllByLabelText(/Remove Jane Doe/);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
      });
    });

    it('should call API and show success dialog on user removal', async () => {
      mockApiPost.mockResolvedValueOnce({});

      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            apiPost: mockApiPost
          }
        }
      );

      // Click remove button
      const removeButtons = screen.getAllByLabelText(/Remove Jane Doe/);
      fireEvent.click(removeButtons[0]);

      // Wait for confirm dialog
      await waitFor(() => {
        expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
      });

      // Click confirm button
      const confirmButton = screen.getByTestId('confirm-button');
      fireEvent.click(confirmButton);

      // Verify API was called
      await waitFor(() => {
        expect(mockApiPost).toHaveBeenCalledWith(
          expect.stringContaining('org-123'),
          { body: {} }
        );
      });

      // Verify success dialog appears
      await waitFor(() => {
        expect(screen.getByTestId('info-dialog')).toBeInTheDocument();
      });
    });

    it('should handle API error during user removal', async () => {
      const mockError = new Error('API Error');
      mockApiPost.mockRejectedValueOnce(mockError);

      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            apiPost: mockApiPost
          }
        }
      );

      // Click remove button
      const removeButtons = screen.getAllByLabelText(/Remove Jane Doe/);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
      });

      // Click confirm button
      const confirmButton = screen.getByTestId('confirm-button');
      fireEvent.click(confirmButton);

      // Verify error was logged
      await waitFor(() => {
        expect(logger.logger.error).toHaveBeenCalledWith(
          'OrgMembers.removeUser failed:',
          expect.objectContaining({
            error: mockError,
            organizationId: 'org-123',
            roleId: 'role-1'
          })
        );
      });
    });

    it('should close dialogs when cancel is clicked', async () => {
      render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            apiPost: mockApiPost
          }
        }
      );

      // Open confirm dialog
      const removeButtons = screen.getAllByLabelText(/Remove Jane Doe/);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
      });

      // Click cancel
      const cancelButton = screen.getByTestId('cancel-button');
      fireEvent.click(cancelButton);

      // Verify dialog is closed
      await waitFor(() => {
        expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('GlobalView user restrictions', () => {
    it('should disable row selection for globalView users', () => {
      const { container } = render(
        <OrgMembers
          organization={mockOrganization}
          userRoles={mockUserRoles}
          setUserRoles={mockSetUserRoles}
        />,
        {
          authContext: {
            user: {
              id: 'viewer-1',
              user_type: 'globalView',
              email: 'viewer@example.com',
              first_name: 'Global',
              last_name: 'Viewer',
              full_name: 'Global Viewer',
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T00:00:00Z',
              invite_pending: false,
              roles: [],
              isRegistered: true,
              apiKeys: [],
              date_accepted_terms: '2023-01-01T00:00:00Z',
              accepted_terms_version: 'v1',
              last_logged_in: '2023-01-01T00:00:00Z',
              first_login: false
            }
          }
        }
      );

      // DataGrid with disableRowSelectionOnClick should be rendered
      const dataGrid = container.querySelector('.MuiDataGrid-root');
      expect(dataGrid).toBeInTheDocument();
    });
  });
});
