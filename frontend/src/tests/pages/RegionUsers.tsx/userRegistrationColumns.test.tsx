import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GridRenderCellParams } from '@mui/x-data-grid';
import {
  getPendingUserColumns,
  getMemberUserColumns,
  organizationCols
} from '@/pages/RegionUsers/UserRegistrationColumns';

describe('Column factories', () => {
  const mockApprove = vi.fn();
  const mockDeny = vi.fn();

  const sampleRow = {
    full_name: 'Test User',
    email: 'test@example.com',
    region_id: '1',
    state: 'NY',
    created_at: '2025-01-01',
    cognito_use_case_description: 'Test Use Case',
    last_logged_in: '2025-01-01',
    organizations_display: 'Org1, Org2',
    org_acronym: 'ORG'
  };

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('getPendingUserColumns', () => {
    it('returns columns with correct fields', () => {
      const columns = getPendingUserColumns({
        userType: 'standard',
        handleApproveClick: mockApprove,
        handleDenyClick: mockDeny
      });

      const fieldNames = columns.map((c) => c.field);
      expect(fieldNames).toEqual([
        'full_name',
        'email',
        'region_id',
        'state',
        'created_at',
        'cognito_use_case_description',
        'status'
      ]);
    });

    it('buttons are disabled for globalView users', () => {
      const columns = getPendingUserColumns({
        userType: 'globalView',
        handleApproveClick: mockApprove,
        handleDenyClick: mockDeny
      });

      const statusCol = columns.find((c) => c.field === 'status')!;
      render(statusCol.renderCell!({ row: sampleRow } as GridRenderCellParams));

      const approveBtn = screen.getByRole('button', { name: /approve/i });
      const denyBtn = screen.getByRole('button', { name: /deny/i });

      expect(approveBtn).toBeDisabled();
      expect(denyBtn).toBeDisabled();
    });

    it('buttons call handlers on click', () => {
      const columns = getPendingUserColumns({
        userType: 'standard',
        handleApproveClick: mockApprove,
        handleDenyClick: mockDeny
      });

      const statusCol = columns.find((c) => c.field === 'status')!;
      render(statusCol.renderCell!({ row: sampleRow } as GridRenderCellParams));

      const approveBtn = screen.getByRole('button', { name: /approve/i });
      const denyBtn = screen.getByRole('button', { name: /deny/i });

      approveBtn.click();
      denyBtn.click();

      expect(mockApprove).toHaveBeenCalledWith(sampleRow);
      expect(mockDeny).toHaveBeenCalledWith(sampleRow);
    });
  });

  describe('getMemberUserColumns', () => {
    it('returns columns with expected fields', () => {
      const columns = getMemberUserColumns();
      const fieldNames = columns.map((c) => c.field);
      expect(fieldNames).toEqual([
        'full_name',
        'email',
        'region_id',
        'state',
        'last_logged_in',
        'organizations_display',
        'org_acronym'
      ]);
    });
  });

  describe('organizationCols', () => {
    it('contains the expected fields', () => {
      const fieldNames = organizationCols.map((c) => c.field);
      expect(fieldNames).toEqual([
        'name',
        'acronym',
        'updated_at',
        'state_name'
      ]);
    });
  });
});
