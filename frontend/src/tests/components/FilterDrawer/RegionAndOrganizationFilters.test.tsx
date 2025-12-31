import React from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render } from '@/test-utils/test-utils';
import { screen } from '@testing-library/react';
import { RegionAndOrganizationFilters } from '../../../components/FilterDrawer/RegionAndOrganizationFilters';
import { useStaticsContext } from '@/context/StaticsContext';
import { useAuthContext } from '@/context/AuthContext';
import { authCtx } from '@/test-utils/authCtx';
import {
  regionalAdminUser,
  globalViewUser,
  globalAdminUser
} from '@/test-utils';
import { mockOrganizations } from '@/test-utils/searchOrg';
import userEvent from '@testing-library/user-event';

//Mock hooks
vi.mock('context/AuthContext');
vi.mock('context/StaticsContext');

describe('RegionAndOrganizationFilters Component', () => {
  const defaultProps = {
    addFilter: vi.fn(),
    removeFilter: vi.fn(),
    filters: [],
    setSearchTerm: vi.fn(),
    searchTerm: '',
    autocompletedResults: [],
    autocompletedSuggestions: [],
    results: [],
    initialFilters: [],
    expanded: false as string | false | undefined
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Region Filters Global Admin User', () => {
    it('renders all region filters correctly', async () => {
      vi.mocked(useStaticsContext).mockReturnValue({
        regions: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
        setRegions: vi.fn()
      });
      const globalAdminAuthCtx = { ...authCtx, user: globalAdminUser };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);
      render(<RegionAndOrganizationFilters {...defaultProps} />);

      const regionAccordion = screen.getByText('Regions');
      expect(regionAccordion).toBeInTheDocument();

      // Check if region filter options are rendered
      expect(screen.getByText('All Regions')).toBeInTheDocument();
      expect(screen.getByText('Region 1')).toBeInTheDocument();
      expect(screen.getByText('Region 2')).toBeInTheDocument();
      expect(screen.getByText('Region 3')).toBeInTheDocument();
      expect(screen.getByText('Region 4')).toBeInTheDocument();
      expect(screen.getByText('Region 5')).toBeInTheDocument();
      expect(screen.getByText('Region 6')).toBeInTheDocument();
      expect(screen.getByText('Region 7')).toBeInTheDocument();
      expect(screen.getByText('Region 8')).toBeInTheDocument();
      expect(screen.getByText('Region 9')).toBeInTheDocument();
      expect(screen.getByText('Region 10')).toBeInTheDocument();
    });
  });

  describe('Region Filters Global View User', () => {
    it('renders all region filters correctly', async () => {
      vi.mocked(useStaticsContext).mockReturnValue({
        regions: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
        setRegions: vi.fn()
      });
      const globalViewAuthCtx = {
        ...authCtx,
        user: globalViewUser
      };
      vi.mocked(useAuthContext).mockReturnValue(globalViewAuthCtx);
      render(<RegionAndOrganizationFilters {...defaultProps} />);

      const regionAccordion = screen.getByText('Regions');
      expect(regionAccordion).toBeInTheDocument();

      // Check if region filter options are rendered
      expect(screen.getByText('All Regions')).toBeInTheDocument();
      expect(screen.getByText('Region 1')).toBeInTheDocument();
      expect(screen.getByText('Region 2')).toBeInTheDocument();
      expect(screen.getByText('Region 3')).toBeInTheDocument();
      expect(screen.getByText('Region 4')).toBeInTheDocument();
      expect(screen.getByText('Region 5')).toBeInTheDocument();
      expect(screen.getByText('Region 6')).toBeInTheDocument();
      expect(screen.getByText('Region 7')).toBeInTheDocument();
      expect(screen.getByText('Region 8')).toBeInTheDocument();
      expect(screen.getByText('Region 9')).toBeInTheDocument();
      expect(screen.getByText('Region 10')).toBeInTheDocument();
    });
  });

  describe('Region Filters Regional Admin User', () => {
    it('renders all region filters correctly', async () => {
      vi.mocked(useStaticsContext).mockReturnValue({
        regions: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
        setRegions: vi.fn()
      });
      const regionalAdminAuthCtx = {
        ...authCtx,
        user: regionalAdminUser
      };
      vi.mocked(useAuthContext).mockReturnValue(regionalAdminAuthCtx);
      render(<RegionAndOrganizationFilters {...defaultProps} />);

      const regionAccordion = screen.getByText('Regions');
      expect(regionAccordion).toBeInTheDocument();

      // Check if region filter options are rendered
      expect(screen.getByText('All Regions')).toBeInTheDocument();
      expect(screen.getByText('Region 1')).toBeInTheDocument();
      expect(screen.getByText('Region 2')).toBeInTheDocument();
      expect(screen.getByText('Region 3')).toBeInTheDocument();
      expect(screen.getByText('Region 4')).toBeInTheDocument();
      expect(screen.getByText('Region 5')).toBeInTheDocument();
      expect(screen.getByText('Region 6')).toBeInTheDocument();
      expect(screen.getByText('Region 7')).toBeInTheDocument();
      expect(screen.getByText('Region 8')).toBeInTheDocument();
      expect(screen.getByText('Region 9')).toBeInTheDocument();
      expect(screen.getByText('Region 10')).toBeInTheDocument();
    });
  });

  describe('Region Filter Standard User', () => {
    it('renders authroized region filters only', async () => {
      vi.mocked(useStaticsContext).mockReturnValue({
        regions: ['3'],
        setRegions: vi.fn()
      });
      // Test User in authCtx has access to region "3" only
      vi.mocked(useAuthContext).mockReturnValue(authCtx);
      render(<RegionAndOrganizationFilters {...defaultProps} />);
      const regionAccordion = screen.getByText('Regions');
      expect(regionAccordion).toBeInTheDocument();

      const disabledAutoCompleteWithUserRegion =
        screen.getByLabelText('Region 3');
      expect(disabledAutoCompleteWithUserRegion).toBeDisabled();
      expect(disabledAutoCompleteWithUserRegion).toBeInTheDocument();
    });
  });

  describe('Organization Filters Global Admin User', () => {
    it('renders organization filters correctly', async () => {
      const globalAdminAuthCtx = {
        ...authCtx,
        user: globalAdminUser,
        apiPost: vi.fn().mockResolvedValue({
          body: {
            hits: {
              hits: mockOrganizations.map((org) => ({ _source: org }))
            }
          }
        })
      };
      vi.mocked(useAuthContext).mockReturnValue(globalAdminAuthCtx);
      render(<RegionAndOrganizationFilters {...defaultProps} />);

      const organizationAccordion = screen.getByText('Organizations');
      expect(organizationAccordion).toBeInTheDocument();

      const user = userEvent.setup();
      await user.click(organizationAccordion);

      const orgAutoComplete = screen.getByLabelText('Search Organizations');
      expect(orgAutoComplete).toBeInTheDocument();

      await user.click(orgAutoComplete);
      screen.debug();
      // Check if organization filter options are rendered

      expect(
        await screen.findByText('Organization 1 (ORG1)')
      ).toBeInTheDocument();
      expect(
        await screen.findByText('Organization 2 (ORG2)')
      ).toBeInTheDocument();
      expect(
        await screen.findByText('Organization 3 (ORG3)')
      ).toBeInTheDocument();
      expect(
        await screen.findByText('Organization 4 (ORG4)')
      ).toBeInTheDocument();
    });
  });
});
