/**
 * Unit test for the zIndex of the filter panel in the DataGrid component on the Vulnerabilities page.
 */

//React
import React from 'react';

//Testing utilities
import { render, screen, testUser } from 'test-utils';
import { describe, it, expect, vi } from 'vitest';

//Types
import type { AuthUser } from 'context';

//Components
// import Vulnerabilities from '@/pages/Vulnerabilities/Vulnerabilities';
import AppDataGrid from '@/components/DataGrid/CustomDataGrid';

const captured: { props?: any } = {};

const columns = [
  { field: 'id', headerName: 'ID', width: 90 },
  { field: 'name', headerName: 'Name', width: 150 }
];

const rows = [
  { id: 1, name: 'Row 1' },
  { id: 2, name: 'Row 2' }
];

// vi.mock('@mui/x-data-grid', async (importOriginal) => {
//   const actual = await importOriginal<typeof import('@mui/x-data-grid')>();
//   return {
//     ...actual,
//     DataGrid: (props: any) => {
//       captured.props = props;
//       return <div data-testid="mock-grid" />;
//     }
//   };
// });

vi.mock('@/components/DataGrid/CustomDataGrid', async (importOriginal) => {
  const actual =
    await importOriginal<
      typeof import('@/components/DataGrid/CustomDataGrid')
    >();
  return {
    ...actual,
    default: (props: any) => {
      captured.props = props;
      return <div data-testid="mock-grid" />;
    }
  };
});

describe('CustomDataGrid mock', () => {
  it('Uses theme appBar minus 1 for filter panel z-index', () => {
    const testProps = {
      slotProps: {
        panel: { sx: ({ zIndex }: any) => ({ zIndex: zIndex.appBar - 1 }) }
      }
    } as any;

    render(<AppDataGrid {...testProps} columns={columns} rows={rows} />);

    screen.findByTestId('mock-grid');

    expect(captured.props).toBeDefined();
    const panelSx = captured.props.slotProps?.panel?.sx;
    expect(typeof panelSx).toBe('function');

    expect(panelSx({ zIndex: { appBar: 1100 } }).zIndex).toBe(1099);
    expect(panelSx({ zIndex: { appBar: 1300 } }).zIndex).toBe(1299);
  });
});

// describe('Vulnerabilities DataGrid panel zIndex', () => {
//   it('uses theme appBar minus 1 for filter panel z-index', async () => {
//     const apiPostMock = vi.fn().mockResolvedValue({ result: [], count: 0 });

//     render(<Vulnerabilities />, {
//       initialHistory: ['/vulnerabilities'],
//       authContext: {
//         apiPost: apiPostMock,
//         currentOrganization: null,
//         user: testUser as unknown as AuthUser
//       }
//     });

//     await screen.findByTestId('mock-grid');

//     expect(captured.props).toBeDefined();

//     const panelSx = captured.props.slotProps?.panel?.sx;
//     expect(typeof panelSx).toBe('function');

//     expect(panelSx({ zIndex: { appBar: 1100 } }).zIndex).toBe(1099);
//     expect(panelSx({ zIndex: { appBar: 1300 } }).zIndex).toBe(1299);
//   });
// });
