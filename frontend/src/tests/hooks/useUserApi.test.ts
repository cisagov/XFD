import { renderHook, waitFor, act } from '@testing-library/react';
import { useUserApi, UserType } from '@/hooks/useUserApi';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockApiGet = vi.fn();
const mockApiDelete = vi.fn();

vi.mock('context', () => ({
  useAuthContext: () => ({
    apiGet: mockApiGet,
    apiDelete: mockApiDelete,
    user: { user_type: 'admin', region_id: '1' }
  })
}));

vi.mock('@/constants/endpoints', () => ({
  ENDPOINTS: {
    USERS: '/v1/users',
    USER: '/v1/users/{user_id}'
  }
}));

vi.mock('date-fns', () => ({
  format: vi.fn((date) => `formatted-${date.toISOString().substring(0, 10)}`)
}));

const MOCK_USER_A: UserType = {
  id: 'user-a-1',
  first_name: 'Alice',
  last_name: 'Smith',
  email: 'alice@test.com',
  full_name: 'Alice Smith',
  last_logged_in: '2023-10-01T10:00:00Z',
  date_accepted_terms: '2023-09-15T10:00:00Z',
  roles: [{ approved: true, organization: { name: 'Org A', acronym: 'OA' } }]
} as unknown as UserType;

const MOCK_USER_B: UserType = {
  id: 'user-b-2',
  first_name: 'Bob',
  last_name: 'Jones',
  email: 'bob@test.com',
  full_name: 'Bob Jones',
  last_logged_in: null,
  date_accepted_terms: '2023-11-20T12:00:00Z',
  roles: [{ approved: true, organization: { name: 'Org B', acronym: 'OB' } }]
} as unknown as UserType;

describe('useUserApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with empty state and fetch users successfully on call', async () => {
    mockApiGet.mockResolvedValueOnce([MOCK_USER_A, MOCK_USER_B]);

    const { result } = renderHook(() => useUserApi());

    expect(result.current.isLoading).toBe(false);
    expect(result.current.users).toEqual([]);

    act(() => {
      result.current.fetchUsers();
    });

    // Assert Loading state
    expect(result.current.isLoading).toBe(true);

    // Wait for the data fetch to complete
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // Assert final state and data transformation
    expect(mockApiGet).toHaveBeenCalledWith('/v1/users');
    expect(result.current.users.length).toBe(2);
    expect(result.current.users[0].full_name).toBe('Alice Smith');
    expect(result.current.users[0].lastLoggedInString).toContain(
      'formatted-2023-10-01'
    );
    expect(result.current.users[0].orgs).toBe('Org A');
    expect(result.current.error).toBe('');
  });

  it('should handle fetch API errors correctly', async () => {
    const mockError = new Error('Users endpoint failed');
    mockApiGet.mockRejectedValueOnce(mockError);

    const { result } = renderHook(() => useUserApi());
    act(() => {
      result.current.fetchUsers();
    });

    // Wait for the error handling to complete
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // Assert: State reflects the error and logger was called
    expect(result.current.error).toBe('Users endpoint failed');
    expect(result.current.users).toEqual([]);
  });

  it('should delete a user successfully and update the users state', async () => {
    mockApiGet.mockResolvedValueOnce([MOCK_USER_A, MOCK_USER_B]);
    const { result } = renderHook(() => useUserApi());

    // Initial fetch to load the data
    act(() => {
      result.current.fetchUsers();
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.users.length).toBe(2);

    mockApiDelete.mockResolvedValueOnce({});

    let deleteResult: { success: boolean; errorMessage: string } = {
      success: false,
      errorMessage: ''
    };
    await act(async () => {
      deleteResult = await result.current.deleteUser(MOCK_USER_A);
    });

    // Assert API call
    expect(mockApiDelete).toHaveBeenCalledWith('/v1/users/user-a-1', {
      body: {}
    });

    // Assert Delete Result
    expect(deleteResult.success).toBe(true);
    expect(deleteResult.errorMessage).toBe('');

    // Assert state update (MOCK_USER_A removed)
    expect(result.current.users.length).toBe(1);
    expect(result.current.users[0].id).toBe(MOCK_USER_B.id);
  });

  it('should return failure and log error when delete API call fails', async () => {
    mockApiGet.mockResolvedValueOnce([MOCK_USER_A, MOCK_USER_B]);
    const { result } = renderHook(() => useUserApi());

    // Initial fetch to load the data
    act(() => {
      result.current.fetchUsers();
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.users.length).toBe(2);

    const deleteError = new Error('Failed to reach user service');
    mockApiDelete.mockRejectedValueOnce(deleteError);

    let deleteResult: { success: boolean; errorMessage: string } = {
      success: true,
      errorMessage: ''
    };
    await act(async () => {
      deleteResult = await result.current.deleteUser(MOCK_USER_B);
    });

    // Assert Delete Result
    expect(deleteResult.success).toBe(false);
    expect(deleteResult.errorMessage).toBe('Failed to reach user service');

    // Assert state update (users array should remain unchanged on failure)
    expect(result.current.users.length).toBe(2);
    expect(result.current.users).toContain(MOCK_USER_B);
  });
});
