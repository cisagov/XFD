import React from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render } from '@/test-utils/test-utils';
import { screen } from '@testing-library/react';
import { useStaticsContext } from '@/context/StaticsContext';
import { useAuthContext } from '@/context/AuthContext';
import { authCtx } from '@/test-utils/authCtx';
import {
  regionalAdminUser,
  globalViewUser,
  globalAdminUser,
  testUser
} from '@/test-utils';
import { testRole } from '@/test-utils/role';
import userEvent from '@testing-library/user-event';
import { act } from 'react';
import { DomainAndIPFilter } from '@/components/FilterDrawer/DomainAndIPFilter';
import { mockIPs } from '@/test-utils/searchIPs';
import { mockDomains } from '@/test-utils/searchDomains';

//Mock hooks
vi.mock('context/AuthContext');
vi.mock('context/StaticsContext');

describe('Domain and IP Filter Component', () => {
  const defaultIpProps = {
    addFilter: vi.fn(),
    removeFilter: vi.fn(),
    filters: [],
    search_field: 'ip'
  };

  const defaultDomainProps = {
    addFilter: vi.fn(),
    removeFilter: vi.fn(),
    filters: [],
    search_field: 'name'
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('IP Autocomplete for Global Admin User', () => {
    it('renders IP Autocomplete for Global Admin', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultIpProps} />);

      const ipAutocomplete = await screen.findByLabelText(/search ip address/i);
      expect(ipAutocomplete).toBeInTheDocument();
    });

    it('renders options when opening IP Autocomplete', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockIPs.map((ip) => ({
                _source: ip
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultIpProps} />);

      const ipAutocomplete = await screen.findByLabelText(/search ip address/i);
      expect(ipAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(ipAutocomplete);
      });

      const option1 = await screen.findByText('192.168.1.1');
      const option2 = await screen.findByText('192.168.1.2');
      const option3 = await screen.findByText('192.168.1.3');
      const option4 = await screen.findByText('192.168.1.4');

      expect(option1).toBeInTheDocument();
      expect(option2).toBeInTheDocument();
      expect(option3).toBeInTheDocument();
      expect(option4).toBeInTheDocument();
    });

    it('narrows down IP options based on user input', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockIPs.map((ip) => ({
                _source: ip
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultIpProps} />);

      const ipAutocomplete = await screen.findByLabelText(/search ip address/i);
      expect(ipAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(ipAutocomplete);
      });

      await act(async () => {
        await user.type(ipAutocomplete, '192.168.1.2');
      });

      const option2 = await screen.findByText('192.168.1.2');
      expect(option2).toBeInTheDocument();

      expect(screen.queryByText('192.168.1.1')).toBeNull();
      expect(screen.queryByText('192.168.1.3')).toBeNull();
      expect(screen.queryByText('192.168.1.4')).toBeNull();
    });
  });

  describe('IP Autocomplete for Regional Admin User', () => {
    it('renders IP Autocomplete for Regional Admin', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultIpProps} />);

      const ipAutocomplete = await screen.findByLabelText(/search ip address/i);
      expect(ipAutocomplete).toBeInTheDocument();
    });

    it('renders options when opening IP Autocomplete', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockIPs.map((ip) => ({
                _source: ip
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultIpProps} />);

      const ipAutocomplete = await screen.findByLabelText(/search ip address/i);
      expect(ipAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(ipAutocomplete);
      });

      const option1 = await screen.findByText('192.168.1.1');
      const option2 = await screen.findByText('192.168.1.2');
      const option3 = await screen.findByText('192.168.1.3');
      const option4 = await screen.findByText('192.168.1.4');

      expect(option1).toBeInTheDocument();
      expect(option2).toBeInTheDocument();
      expect(option3).toBeInTheDocument();
      expect(option4).toBeInTheDocument();
    });

    it('narrows down IP options based on user input', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockIPs.map((ip) => ({
                _source: ip
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultIpProps} />);

      const ipAutocomplete = await screen.findByLabelText(/search ip address/i);
      expect(ipAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(ipAutocomplete);
      });

      await act(async () => {
        await user.type(ipAutocomplete, '192.168.1.2');
      });
      const option2 = await screen.findByText('192.168.1.2');
      expect(option2).toBeInTheDocument();

      expect(screen.queryByText('192.168.1.1')).not.toBeInTheDocument();
      expect(screen.queryByText('192.168.1.3')).not.toBeInTheDocument();
      expect(screen.queryByText('192.168.1.4')).not.toBeInTheDocument();
    });
  });
  describe('Domain Autocomplete for Global Admin User', () => {
    it('renders Domain Autocomplete for Global Admin', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultDomainProps} />);

      const domainAutocomplete = await screen.findByLabelText(/search domain/i);
      expect(domainAutocomplete).toBeInTheDocument();
    });

    it('renders options when opening Domain Autocomplete', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockDomains.map((domain) => ({
                _source: domain
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultDomainProps} />);

      const domainAutocomplete =
        await screen.findByLabelText(/search domains/i);
      expect(domainAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(domainAutocomplete);
      });

      const option1 = await screen.findByText('example1.com');
      const option2 = await screen.findByText('example2.com');
      const option3 = await screen.findByText('example3.com');
      const option4 = await screen.findByText('example4.com');

      expect(option1).toBeInTheDocument();
      expect(option2).toBeInTheDocument();
      expect(option3).toBeInTheDocument();
      expect(option4).toBeInTheDocument();
    });

    it('narrows down domain options based on user input', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockDomains.map((domain) => ({
                _source: domain
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultDomainProps} />);

      const domainAutocomplete =
        await screen.findByLabelText(/search domains/i);
      expect(domainAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(domainAutocomplete);
      });

      await act(async () => {
        await user.type(domainAutocomplete, 'example2');
      });

      const option2 = await screen.findByText('example2.com');
      expect(option2).toBeInTheDocument();

      expect(screen.queryByText('example1.com')).not.toBeInTheDocument();
      expect(screen.queryByText('example3.com')).not.toBeInTheDocument();
      expect(screen.queryByText('example4.com')).not.toBeInTheDocument();
    });
  });

  describe('Domain Autocomplete for Regional Admin User', () => {
    it('renders Domain Autocomplete for Regional Admin', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultDomainProps} />);

      const domainAutocomplete = await screen.findByLabelText(/search domain/i);
      expect(domainAutocomplete).toBeInTheDocument();
    });

    it('renders options when opening Domain Autocomplete', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockDomains.map((domain) => ({
                _source: domain
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultDomainProps} />);

      const domainAutocomplete =
        await screen.findByLabelText(/search domains/i);
      expect(domainAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(domainAutocomplete);
      });

      const option1 = await screen.findByText('example1.com');
      const option2 = await screen.findByText('example2.com');
      const option3 = await screen.findByText('example3.com');
      const option4 = await screen.findByText('example4.com');

      expect(option1).toBeInTheDocument();
      expect(option2).toBeInTheDocument();
      expect(option3).toBeInTheDocument();
      expect(option4).toBeInTheDocument();
    });

    it('narrows down domain options based on user input', async () => {
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockDomains.map((domain) => ({
                _source: domain
              }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);

      render(<DomainAndIPFilter {...defaultDomainProps} />);

      const domainAutocomplete =
        await screen.findByLabelText(/search domains/i);
      expect(domainAutocomplete).toBeInTheDocument();

      const user = userEvent.setup();
      await act(async () => {
        await user.click(domainAutocomplete);
      });

      await act(async () => {
        await user.type(domainAutocomplete, 'example2');
      });

      const option2 = await screen.findByText('example2.com');
      expect(option2).toBeInTheDocument();

      expect(screen.queryByText('example1.com')).not.toBeInTheDocument();
      expect(screen.queryByText('example3.com')).not.toBeInTheDocument();
      expect(screen.queryByText('example4.com')).not.toBeInTheDocument();
    });
  });
});
