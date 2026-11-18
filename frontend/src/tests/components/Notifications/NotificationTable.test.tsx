import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import NotificationTable from '@/components/Notifications/NotificationTable';

vi.mock('@/components/DataGrid/CustomDataGrid', () => ({
  default: ({
    children,
    slotProps,
    slots,
    pageSizeOptions,
    showToolbar
  }: any) => {
    const Toolbar = slots?.toolbar;
    return (
      <div data-testid="notification-grid">
        {showToolbar && Toolbar && <Toolbar {...slotProps?.toolbar} />}
        <span data-testid="page-size-options">{pageSizeOptions.join(',')}</span>
        {children}
      </div>
    );
  }
}));

vi.mock('@/components/DataGrid/CustomToolbar', () => ({
  default: ({ disableExport, hasActiveFilters }: any) => (
    <div data-testid="notification-toolbar">
      <span data-testid="disable-export">{String(disableExport)}</span>
      <span data-testid="has-active-filters">{String(hasActiveFilters)}</span>
    </div>
  )
}));

describe('NotificationTable', () => {
  it('renders the standardized toolbar and shared page-size options', () => {
    render(
      <NotificationTable title="Inactive Notifications" rows={[]} columns={[]}>
        <span>Additional notification information</span>
      </NotificationTable>
    );

    expect(screen.getByTestId('notification-grid')).toBeInTheDocument();
    expect(screen.getByTestId('notification-toolbar')).toBeInTheDocument();
    expect(screen.getByTestId('disable-export').textContent).toBe('true');
    expect(screen.getByTestId('has-active-filters').textContent).toBe('false');
    expect(screen.getByTestId('page-size-options').textContent).toBe(
      '15,30,50,100'
    );
    expect(
      screen.getByText('Additional notification information')
    ).toBeInTheDocument();
  });
});
