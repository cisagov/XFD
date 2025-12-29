import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { RegionAndOrganizationFilters } from '../../../components/FilterDrawer/RegionAndOrganizationFilters';

const mockOnRegionChange = vi.fn();
const mockOnOrganizationChange = vi.fn();

//   beforeEach(() => {
//     render(
//       <RegionAndOrganizationFilters
//         regions={mockRegions}
//         organizations={mockOrganizations}
//         selectedRegions={[]}
//         selectedOrganizations={[]}
//         onRegionChange={mockOnRegionChange}
//         onOrganizationChange={mockOnOrganizationChange}
//       />
//     );
//   });
describe('RegionAndOrganizationFilters Component', () => {
  const mockRegions = [
    { id: '1', name: 'North America' },
    { id: '2', name: 'Europe' }
  ];

  const mockOrganizations = [
    { id: '1', name: 'Org A' },
    { id: '2', name: 'Org B' }
  ];

  it('renders region filters correctly', () => {
    mockRegions.forEach((region) => {
      expect(screen.getByLabelText(region.name)).toBeInTheDocument();
    });
  });
});
