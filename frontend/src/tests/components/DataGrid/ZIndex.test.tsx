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
import Vulnerabilities from '@/pages/Vulnerabilities/Vulnerabilities';

const captured: { props?: any } = {};

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

describe('Vulnerabilities DataGrid panel zIndex', () => {
  it('uses theme appBar minus 1 for filter panel z-index', async () => {
    const apiPostMock = vi.fn().mockResolvedValue({ result: [], count: 0 });

    render(<Vulnerabilities />, {
      initialHistory: ['/vulnerabilities'],
      authContext: {
        apiPost: apiPostMock,
        currentOrganization: null,
        user: testUser as unknown as AuthUser
      }
    });

    await screen.findByTestId('mock-grid');

    expect(captured.props).toBeDefined();

    const panelSx = captured.props.slotProps?.panel?.sx;
    expect(typeof panelSx).toBe('function');

    expect(panelSx({ zIndex: { appBar: 1100 } }).zIndex).toBe(1099);
    expect(panelSx({ zIndex: { appBar: 1300 } }).zIndex).toBe(1299);
  });
});
