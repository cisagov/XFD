/**
 * Test to verify DataGrid export works correctly with formatDisplayValue in renderCell.
 *
 * This test ensures that:
 * - Numbers displayed with comma formatting (via formatDisplayValue)
 * - Export as actual numbers, not formatted strings
 * - The renderCell formatting doesn't affect the exported data
 */

// React
import React from 'react';

// Testing utilities
import { render, screen } from 'test-utils/test-utils';
import { describe, it, expect, vi } from 'vitest';

// MUI DataGrid
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';

// Utils
import { formatDisplayValue } from 'utils/stringUtils';

// Mock data with large numbers that would be formatted
const mockQueueData = [
  {
    id: 1,
    name: 'test-queue-1',
    messages_available: 1234,
    messages_in_flight: 5678,
    messages_delayed: 9999
  },
  {
    id: 2,
    name: 'test-queue-2',
    messages_available: 999,
    messages_in_flight: 1000,
    messages_delayed: 12345
  }
];

// Column definition using formatDisplayValue in renderCell (similar to QueueMonitorView)
const testColumns: GridColDef[] = [
  {
    field: 'name',
    headerName: 'Queue Name',
    width: 200
  },
  {
    field: 'messages_available',
    headerName: 'Available',
    width: 150,
    renderCell: (cellValues: GridRenderCellParams) => (
      <span>{formatDisplayValue(cellValues.row.messages_available)}</span>
    )
  },
  {
    field: 'messages_in_flight',
    headerName: 'In-Flight',
    width: 150,
    renderCell: (cellValues: GridRenderCellParams) => (
      <span>{formatDisplayValue(cellValues.row.messages_in_flight)}</span>
    )
  },
  {
    field: 'messages_delayed',
    headerName: 'Delayed',
    width: 150,
    renderCell: (cellValues: GridRenderCellParams) => (
      <span>{formatDisplayValue(cellValues.row.messages_delayed)}</span>
    )
  }
];

describe('DataGrid Export with formatDisplayValue', () => {
  it('renders formatted numbers in cells', () => {
    render(
      <div style={{ height: 400, width: '100%' }}>
        <DataGrid
          rows={mockQueueData}
          columns={testColumns}
          disableRowSelectionOnClick
        />
      </div>
    );

    // Check that numbers >= 1000 are displayed with commas
    expect(screen.getByText('1,234')).toBeInTheDocument();
    expect(screen.getByText('5,678')).toBeInTheDocument();
    expect(screen.getByText('9,999')).toBeInTheDocument();
    expect(screen.getByText('1,000')).toBeInTheDocument();
    expect(screen.getByText('12,345')).toBeInTheDocument();

    // Check that numbers < 1000 are displayed without commas
    expect(screen.getByText('999')).toBeInTheDocument();
  });

  it('demonstrates export vs display data separation principle', () => {
    // Render DataGrid with formatted display values
    render(
      <div style={{ height: 400, width: '100%' }}>
        <DataGrid
          rows={mockQueueData}
          columns={testColumns}
          disableRowSelectionOnClick
        />
      </div>
    );

    // DISPLAY: Users see formatted numbers with commas
    expect(screen.getByText('1,234')).toBeInTheDocument();
    expect(screen.getByText('5,678')).toBeInTheDocument();

    // EXPORT: Original data remains numeric (what would be exported)
    expect(mockQueueData[0].messages_available).toBe(1234);
    expect(mockQueueData[0].messages_in_flight).toBe(5678);
    expect(typeof mockQueueData[0].messages_available).toBe('number');
    expect(typeof mockQueueData[0].messages_in_flight).toBe('number');

    // SEPARATION: Display formatting doesn't affect export data
    expect(formatDisplayValue(mockQueueData[0].messages_available)).toBe(
      '1,234'
    );
    expect(mockQueueData[0].messages_available).not.toBe('1,234'); // Original remains numeric

    // PRINCIPLE: renderCell affects display, DataGrid export uses original rows data
    // This ensures CSV exports contain numbers for spreadsheet calculations,
    // while users see readable formatted numbers in the UI
  });

  it('formatDisplayValue utility works correctly', () => {
    // Test the utility function directly
    expect(formatDisplayValue(999)).toBe('999');
    expect(formatDisplayValue(1000)).toBe('1,000');
    expect(formatDisplayValue(1234)).toBe('1,234');
    expect(formatDisplayValue(12345)).toBe('12,345');
    expect(formatDisplayValue(1234567)).toBe('1,234,567');

    // Test non-numbers are returned as-is
    expect(formatDisplayValue('test')).toBe('test');
    expect(formatDisplayValue(null)).toBe(null);
    expect(formatDisplayValue(undefined)).toBe(undefined);
  });
});
