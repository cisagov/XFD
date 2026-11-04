// React
import React from 'react';
import { act } from 'react';

// Testing Library
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Testing utilities
import { authCtx } from '@/test-utils/authCtx';
import { render } from '@/test-utils/test-utils';
import {
  regionalAdminUser,
  globalViewUser,
  globalAdminUser
} from '@/test-utils';
import { mockCVEs } from '@/test-utils/searchCVEs';

// Components
import { CVEFilter } from '@/components/FilterDrawer/CVEFilter';

//Context
import { useAuthContext } from '@/context/AuthContext';

//Mock hooks
vi.mock('context/AuthContext');
vi.mock('context/StaticsContext');

describe('CVE Filter Component', () => {
  const defaultCVEProps = {
    addFilter: vi.fn(),
    removeFilter: vi.fn(),
    filters: []
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('CVE Autocomplete for Global Admin User', () => {
    it('renders CVE Autocomplete for Global Admin', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();
    });

    it('renders options when opening CVE Autocomplete', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockCVEs.map((cve) => ({
                _source: cve
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(cveAutocomplete);
      });

      const option1 = await screen.findByText('CVE-2021-1234');
      const option2 = await screen.findByText('CVE-2021-2345');
      const option3 = await screen.findByText('CVE-2021-3456');
      const option4 = await screen.findByText('CVE-2021-4567');

      expect(option1).toBeInTheDocument();
      expect(option2).toBeInTheDocument();
      expect(option3).toBeInTheDocument();
      expect(option4).toBeInTheDocument();
    });

    it('narrows down CVE options based on user input', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockCVEs.map((cve) => ({
                _source: cve
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(cveAutocomplete);
      });

      await act(async () => {
        await user.type(cveAutocomplete, 'CVE-2021-2345');
      });

      const option2 = await screen.findByText('CVE-2021-2345');
      expect(option2).toBeInTheDocument();

      expect(screen.queryByText('CVE-2021-1234')).toBeNull();
      expect(screen.queryByText('CVE-2021-3456')).toBeNull();
      expect(screen.queryByText('CVE-2021-4567')).toBeNull();
    });
  });

  describe('CVE Autocomplete for Global View User', () => {
    it('renders CVE Autocomplete for Global View', async () => {
      const globalViewAuthCtx = {
        ...authCtx,
        user: globalViewUser
      };
      vi.mocked(useAuthContext).mockReturnValue(globalViewAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();
    });

    it('renders options when opening CVE Autocomplete', async () => {
      const globalViewAuthCtx = {
        ...authCtx,
        user: globalViewUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockCVEs.map((cve) => ({
                _source: cve
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalViewAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(cveAutocomplete);
      });

      const option1 = await screen.findByText('CVE-2021-1234');
      const option2 = await screen.findByText('CVE-2021-2345');
      const option3 = await screen.findByText('CVE-2021-3456');
      const option4 = await screen.findByText('CVE-2021-4567');

      expect(option1).toBeInTheDocument();
      expect(option2).toBeInTheDocument();
      expect(option3).toBeInTheDocument();
      expect(option4).toBeInTheDocument();
    });

    it('narrows down CVE options based on user input', async () => {
      const globalViewAuthCtx = {
        ...authCtx,
        user: globalViewUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockCVEs.map((cve) => ({
                _source: cve
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalViewAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(cveAutocomplete);
      });

      await act(async () => {
        await user.type(cveAutocomplete, 'CVE-2021-2345');
      });
      const option2 = await screen.findByText('CVE-2021-2345');
      expect(option2).toBeInTheDocument();

      expect(screen.queryByText('CVE-2021-1234')).not.toBeInTheDocument();
      expect(screen.queryByText('CVE-2021-3456')).not.toBeInTheDocument();
      expect(screen.queryByText('CVE-2021-4567')).not.toBeInTheDocument();
    });
  });

  describe('CVE Autocomplete for Regional Admin User', () => {
    it('renders CVE Autocomplete for Regional Admin', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();
    });

    it('renders options when opening CVE Autocomplete', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockCVEs.map((cve) => ({
                _source: cve
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(cveAutocomplete);
      });

      const option1 = await screen.findByText('CVE-2021-1234');
      const option2 = await screen.findByText('CVE-2021-2345');
      const option3 = await screen.findByText('CVE-2021-3456');
      const option4 = await screen.findByText('CVE-2021-4567');

      expect(option1).toBeInTheDocument();
      expect(option2).toBeInTheDocument();
      expect(option3).toBeInTheDocument();
      expect(option4).toBeInTheDocument();
    });

    it('narrows down CVE options based on user input', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockCVEs.map((cve) => ({
                _source: cve
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<CVEFilter {...defaultCVEProps} />);

      const cveAutocomplete = await screen.findByLabelText(/search cve/i);
      expect(cveAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(cveAutocomplete);
      });

      await act(async () => {
        await user.type(cveAutocomplete, 'CVE-2021-2345');
      });
      const option2 = await screen.findByText('CVE-2021-2345');
      expect(option2).toBeInTheDocument();

      expect(screen.queryByText('CVE-2021-1234')).not.toBeInTheDocument();
      expect(screen.queryByText('CVE-2021-3456')).not.toBeInTheDocument();
      expect(screen.queryByText('CVE-2021-4567')).not.toBeInTheDocument();
    });
  });
});
