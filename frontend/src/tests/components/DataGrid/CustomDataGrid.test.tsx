/**
 * Unit tests for the CustomDataGrid component.
 */

//React
import React from 'react';

//Testing utilities
import { render, screen } from 'test-utils';
import { describe, it, expect, vi } from 'vitest';

//Components
import CustomDataGrid from '@/components/DataGrid/CustomDataGrid';

const captured: { props?: any } = {};

const columns = [
  { field: 'id', headerName: 'ID', width: 90 },
  { field: 'name', headerName: 'Name', width: 150 }
];

const rows = [
  { id: 1, name: 'Row 1' },
  { id: 2, name: 'Row 2' }
];

// Mock the DataGrid component to capture its props for testing z-index adjustments.
vi.mock('@mui/x-data-grid', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@mui/x-data-grid')>();
  return {
    ...actual,
    DataGrid: (props: any) => {
      captured.props = props;
      return <div data-testid="mock-grid" />;
    }
  };
});

// Test suite for the CustomDataGrid component.
describe('CustomDataGrid', () => {
  it('uses Theme appBar minus 1 for filter panel z-index', async () => {
    render(<CustomDataGrid columns={columns} rows={rows} />);

    await screen.findByTestId('mock-grid');

    expect(captured.props).toBeDefined();
    const panelSx = captured.props.slotProps?.panel?.sx;
    expect(typeof panelSx).toBe('function');

    expect(panelSx({ zIndex: { appBar: 1100 } }).zIndex).toBe(1099);
    expect(panelSx({ zIndex: { appBar: 1300 } }).zIndex).toBe(1299);
  });
});
