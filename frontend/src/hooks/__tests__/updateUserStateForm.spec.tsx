import React from 'react';
import {
  render,
  fireEvent,
  waitFor,
  screen
} from '../../test-utils/test-utils';
import { testUser } from '../../test-utils/user';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { UpdateStateForm } from '../../components/UpdateUserStateForm/UpdateUserStateForm';

vi.mock('@/constants/constants', () => ({
  STATE_OPTIONS: ['California', 'Texas', 'New York', 'Florida']
}));

describe('UpdateStateForm component', () => {
  const mockProps = {
    open: true,
    user_id: 'test-user-123',
    onClose: vi.fn()
  };

  const mockAuthContext = {
    apiPost: vi.fn(),
    apiGet: vi.fn(),
    logout: vi.fn(),
    user: {
      ...testUser,
      user_type: 'standard' as const,
      invite_pending: false
    }
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the dialog when open is true', () => {
    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    expect(screen.getByText('Update State Information')).toBeInTheDocument();
    expect(screen.getByLabelText('Select Your State')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('does not render when open is false', () => {
    render(<UpdateStateForm {...mockProps} open={false} />, {
      authContext: mockAuthContext
    });

    expect(
      screen.queryByText('Update State Information')
    ).not.toBeInTheDocument();
  });

  it('shows state options in select dropdown', async () => {
    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const selectElement = screen.getByRole('combobox');
    fireEvent.mouseDown(selectElement);

    await waitFor(() => {
      expect(screen.getByText('California')).toBeInTheDocument();
      expect(screen.getByText('Texas')).toBeInTheDocument();
      expect(screen.getByText('New York')).toBeInTheDocument();
      expect(screen.getByText('Florida')).toBeInTheDocument();
    });
  });

  it('updates state value when option is selected', async () => {
    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const selectElement = screen.getByRole('combobox');
    fireEvent.mouseDown(selectElement);

    await waitFor(() => {
      const californiaOption = screen.getByText('California');
      fireEvent.click(californiaOption);
    });

    // Check that the selected value appears in the select
    await waitFor(() => {
      expect(screen.getByDisplayValue('California')).toBeInTheDocument();
    });
  });

  it('calls logout when Cancel button is clicked', () => {
    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockAuthContext.logout).toHaveBeenCalledOnce();
  });

  it('calls apiPost when Save button is clicked with valid state', async () => {
    mockAuthContext.apiPost.mockResolvedValue({});
    mockAuthContext.apiGet.mockResolvedValue([]);

    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const selectElement = screen.getByRole('combobox');
    fireEvent.mouseDown(selectElement);

    await waitFor(() => {
      const californiaOption = screen.getByText('California');
      fireEvent.click(californiaOption);
    });

    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockAuthContext.apiPost).toHaveBeenCalledWith(
        '/v2/update_user/test-user-123',
        {
          body: { state: 'California' }
        }
      );
    });
  });

  it('shows loading state when save is in progress', async () => {
    mockAuthContext.apiPost.mockImplementation(() => new Promise(() => {}));

    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const selectElement = screen.getByRole('combobox');
    fireEvent.mouseDown(selectElement);

    await waitFor(() => {
      const californiaOption = screen.getByText('California');
      fireEvent.click(californiaOption);
    });

    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  it('shows error message when save fails', async () => {
    mockAuthContext.apiPost.mockRejectedValue(new Error('Network error'));

    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const selectElement = screen.getByRole('combobox');
    fireEvent.mouseDown(selectElement);

    await waitFor(() => {
      const californiaOption = screen.getByText('California');
      fireEvent.click(californiaOption);
    });

    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          'Something went wrong updating the state. Please try again.'
        )
      ).toBeInTheDocument();
    });
  });

  it('calls onClose after successful save', async () => {
    mockAuthContext.apiPost.mockResolvedValue({});
    mockAuthContext.apiGet.mockResolvedValue([]);

    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const selectElement = screen.getByRole('combobox');
    fireEvent.mouseDown(selectElement);

    await waitFor(() => {
      const californiaOption = screen.getByText('California');
      fireEvent.click(californiaOption);
    });

    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockProps.onClose).toHaveBeenCalledOnce();
    });
  });

  it('disables Cancel button when user has pending invite', () => {
    const authContextWithPendingInvite = {
      ...mockAuthContext,
      user: {
        ...mockAuthContext.user,
        invite_pending: true
      }
    };

    render(<UpdateStateForm {...mockProps} />, {
      authContext: authContextWithPendingInvite
    });

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    expect(cancelButton).toBeDisabled();
  });

  it('saves state to localStorage after successful API call', async () => {
    mockAuthContext.apiPost.mockResolvedValue({});
    mockAuthContext.apiGet.mockResolvedValue([]);

    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const selectElement = screen.getByRole('combobox');
    fireEvent.mouseDown(selectElement);

    await waitFor(() => {
      const californiaOption = screen.getByText('California');
      fireEvent.click(californiaOption);
    });

    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(setItemSpy).toHaveBeenCalledWith('user_state', 'California');
    });

    setItemSpy.mockRestore();
  });

  it('dispatches maintenance-blocked event when active maintenance found', async () => {
    mockAuthContext.apiPost.mockResolvedValue({});
    mockAuthContext.apiGet.mockResolvedValue([
      {
        status: 'active',
        maintenance_type: 'major',
        start_datetime: new Date(Date.now() - 1000).toISOString(),
        end_datetime: new Date(Date.now() + 1000).toISOString(),
        message: 'System maintenance in progress'
      }
    ]);

    const dispatchEventSpy = vi.spyOn(window, 'dispatchEvent');

    render(<UpdateStateForm {...mockProps} />, {
      authContext: mockAuthContext
    });

    const selectElement = screen.getByRole('combobox');
    fireEvent.mouseDown(selectElement);

    await waitFor(() => {
      const californiaOption = screen.getByText('California');
      fireEvent.click(californiaOption);
    });

    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(dispatchEventSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'maintenance-blocked',
          detail: { message: 'System maintenance in progress' }
        })
      );
    });

    dispatchEventSpy.mockRestore();
  });
});
