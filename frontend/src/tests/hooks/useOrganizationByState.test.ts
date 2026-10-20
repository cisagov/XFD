import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useOrganizationsByState } from '@/hooks/useOrganizationsByState';
import type { Organization } from 'types';
import { useAuthContext } from 'context';
import { ApiError } from '@/hooks/useApi';
import { jsonResponse } from '@/test-utils/jsonResponse';
import { ENDPOINTS } from '@/constants/endpoints';
import { getStateAbbreviation } from '@/utils/stringUtils';
import { logger } from '@/utils/logger';

vi.mock('context', () => ({
  useAuthContext: vi.fn()
}));

vi.mock('@/utils/stringUtils', () => ({
  getStateAbbreviation: vi.fn()
}));

vi.mock('@/utils/logger', () => ({
  logger: {
    error: vi.fn()
  }
}));

describe('useOrganizationsByState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Verifies the hook resolves the supplied state to an abbreviation,
   * fetches organizations using the state endpoint, and exposes the results.
   */
  it('fetches organizations for a valid state and exposes them', async () => {
    const mockOrganizations: Organization[] = [
      { id: 'org-1', name: 'Ohio Organization', acronym: 'OO' } as Organization
    ];

    vi.mocked(getStateAbbreviation).mockReturnValue('OH');

    const apiGet = vi.fn().mockResolvedValue(mockOrganizations);
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => useOrganizationsByState('Ohio'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(getStateAbbreviation).toHaveBeenCalledWith('Ohio');
    expect(result.current.organizations).toEqual(mockOrganizations);
    expect(result.current.errorMessage).toBe('');

    expect(apiGet).toHaveBeenCalledTimes(1);
    expect(apiGet).toHaveBeenCalledWith(
      ENDPOINTS.ORGANIZATIONS_STATE.replace('{state}', 'OH')
    );
  });

  /**
   * Verifies the hook does not make an API request when the supplied state
   * cannot be resolved to a valid state abbreviation.
   */
  it('does not call the API when the state abbreviation is unavailable', async () => {
    vi.mocked(getStateAbbreviation).mockReturnValue('');

    const apiGet = vi.fn();
    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() =>
      useOrganizationsByState('Invalid State')
    );

    await waitFor(() => {
      expect(getStateAbbreviation).toHaveBeenCalledWith('Invalid State');
    });

    expect(apiGet).not.toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.organizations).toEqual([]);
    expect(result.current.errorMessage).toBe('');
    expect(logger.error).not.toHaveBeenCalled();
  });

  /**
   * Verifies the hook clears the organization list, exposes the API error
   * message, and logs the failure when the request fails.
   */
  it('sets errorMessage and logs an error when the API request fails', async () => {
    vi.mocked(getStateAbbreviation).mockReturnValue('CA');

    const response = jsonResponse(
      {
        detail: 'Token has expired'
      },
      {
        status: 401,
        statusText: 'Unauthorized',
        headers: {
          'x-amzn-requestid': 'request-id'
        }
      }
    );

    const error = new ApiError(response, { detail: 'Token has expired' });
    const apiGet = vi.fn().mockRejectedValue(error);

    vi.mocked(useAuthContext).mockReturnValue({
      apiGet
    } as unknown as ReturnType<typeof useAuthContext>);

    const { result } = renderHook(() => useOrganizationsByState('California'));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(apiGet).toHaveBeenCalledWith(
      ENDPOINTS.ORGANIZATIONS_STATE.replace('{state}', 'CA')
    );
    expect(result.current.organizations).toEqual([]);
    expect(result.current.errorMessage).toBe('Token has expired');

    expect(logger.error).toHaveBeenCalledWith(
      'UseOrganizationsByState failed',
      {
        error,
        state: 'California'
      }
    );
  });
});
