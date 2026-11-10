import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from 'test-utils';
import userEvent from '@testing-library/user-event';
import { ENDPOINTS } from '@/constants/endpoints';
import ScansWidget from '@/components/Metrics/Widgets/ScansWidget';

vi.mock('components/Dashboard/InfoLabel', () => ({
  default: ({ label }: { label: string }) => <h2>{label}</h2>
}));

vi.mock('@mui/x-charts/SparkLineChart', () => ({
  SparkLineChart: () => <div data-testid="sparkline" />
}));

vi.mock('@/components/DataGrid/CustomToolbar', () => ({
  default: ({
    exportTitle,
    hasActiveFilters
  }: {
    exportTitle?: string;
    hasActiveFilters?: boolean;
  }) => (
    <div data-testid={`metrics-toolbar-${exportTitle}`}>
      <span data-testid={`metrics-filter-badge-${exportTitle}`}>
        {String(hasActiveFilters)}
      </span>
    </div>
  )
}));

vi.mock('@/components/DataGrid/CustomDataGrid', () => ({
  default: ({
    rows,
    slotProps,
    slots,
    onCellClick,
    onFilterModelChange,
    filterModel
  }: any) => {
    const Toolbar = slots?.toolbar;
    const gridName = rows[0]?.http_status ? 'details' : 'summary';

    return (
      <div data-testid={`${gridName}-grid`}>
        {Toolbar && <Toolbar {...slotProps?.toolbar} />}
        <span data-testid={`${gridName}-filter-model`}>
          {filterModel?.items?.length ?? 0}
        </span>
        <button
          type="button"
          data-testid={`${gridName}-apply-filter`}
          onClick={() =>
            onFilterModelChange({
              items: [
                { field: 'name', operator: 'contains', value: 'censys' }
              ]
            })
          }
        >
          Apply filter
        </button>
        {rows.map((row: { id: string }) => (
          <button
            type="button"
            key={row.id}
            onClick={() => onCellClick?.({ row: { id: row.id } })}
          >
            {row.id}
          </button>
        ))}
      </div>
    );
  }
}));

describe('ScansWidget', () => {
  const summaries = {
    scans: [
      {
        id: 'scan-1',
        name: 'censys',
        total_orgs: 2,
        org_counts_by_status: [{ http_status: 200, org_count: 2 }]
      },
      {
        id: 'scan-2',
        name: 'amass',
        total_orgs: 1,
        org_counts_by_status: [{ http_status: 404, org_count: 1 }]
      }
    ],
    metrics_window_days: 7
  };

  const details = (id: string, name: string) => ({
    id,
    name,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    frequency: 60,
    last_run: null,
    total_orgs: 2,
    metrics_window_days: 7,
    daily_status_counts: [
      {
        http_status: 200,
        daily_counts: [{ date: '2024-01-01', count: 2 }]
      }
    ]
  });

  it('renders the summary grid with an inactive filter badge', async () => {
    const apiGet = vi.fn().mockResolvedValue(summaries);

    render(<ScansWidget />, { authContext: { apiGet } });

    expect(await screen.findByTestId('summary-grid')).toBeInTheDocument();
    expect(
      screen.getByTestId('metrics-filter-badge-Scan Result Summary').textContent
    ).toBe('false');
    expect(apiGet).toHaveBeenCalledWith(ENDPOINTS.METRICS_SCANS);
  });

  it('clears detail filters when a different scan is selected', async () => {
    const user = userEvent.setup();
    const apiGet = vi.fn((endpoint: string) => {
      if (endpoint === ENDPOINTS.METRICS_SCANS) {
        return Promise.resolve(summaries);
      }
      if (endpoint.includes('scan-1')) {
        return Promise.resolve(details('scan-1', 'censys'));
      }
      return Promise.resolve(details('scan-2', 'amass'));
    });

    render(<ScansWidget />, { authContext: { apiGet } });

    await screen.findByTestId('summary-grid');
    await user.click(await screen.findByRole('button', { name: 'scan-1' }));

    await waitFor(() => {
      expect(screen.getByTestId('details-grid')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('details-apply-filter'));
    await waitFor(() => {
      expect(
        screen.getByTestId('metrics-filter-badge-HTTP Status Trends').textContent
      ).toBe('true');
    });

    await user.click(screen.getByRole('button', { name: 'scan-2' }));

    await waitFor(() => {
      expect(screen.getByTestId('details-filter-model').textContent).toBe('0');
      expect(
        screen.getByTestId('metrics-filter-badge-HTTP Status Trends').textContent
      ).toBe('false');
    });
  });
});
