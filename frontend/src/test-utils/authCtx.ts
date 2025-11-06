import { AuthContextType } from 'context';
import { testUser } from './user';
import { vi } from 'vitest';

export const authCtx: AuthContextType = {
  user: testUser,
  token: 'some-test-token-never-verified',
  currentOrganization: null,
  showAllOrganizations: false,
  showMaps: false,
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  setUser: vi.fn(),
  setOrganization: vi.fn(),
  setShowMaps: vi.fn(),
  setShowAllOrganizations: vi.fn(),
  setFeedbackMessage: vi.fn(),
  refreshUser: vi.fn(),
  setLoading: vi.fn(),
  apiGet: vi.fn(),
  apiDelete: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  maximumRole: 'user',
  touVersion: 'v1-user',
  userMustSign: false,
  user_type: '',
  isLoggingOut: false
};
