import React, { createRef } from 'react';

// Testing Library
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

// Component and types
import { ScanForm, ScanFormRef, ScanFormValues } from '@/pages';

import { OrganizationOption } from '@/types/organization';
import { ScanSchema } from '@/types';

const organizationOptions: OrganizationOption[] = [
  {
    label: 'Organization One',
    value: 'org-1'
  },
  {
    label: 'Organization Two',
    value: 'org-2'
  }
];

const scanSchema: ScanSchema = {
  censys: {
    description: 'Default Censys scan',
    global: false,
    max_concurrent_tasks: 5,
    type: 'fargate',
    is_passive: false

  },
  vulnScanningSync: {
    description: 'Synchronizes vulnerability data',
    global: false,
    max_concurrent_tasks: 10,
    type: 'fargate',
    is_passive: false
  },
  unlimitedScan: {
    description: 'A scan without a concurrent-task limit',
    global: false,
    type: 'fargate',
    is_passive: false
  }
};

const propValues: ScanFormValues = {
  name: 'censys',
  arguments: {},
  organizations: [],
  frequency: 1,
  frequencyUnit: 'day',
  is_granular: false,
  is_single_scan: false,
  concurrent_tasks: 1,
  useDateRange: false
};

const renderScanForm = (
  overrides: Partial<React.ComponentProps<typeof ScanForm>> = {}
) => {
  const ref = createRef<ScanFormRef>();
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  const onValidityChange = vi.fn();

  const renderResult = render(
    <ScanForm
      ref={ref}
      propValues={propValues}
      organizationOption={organizationOptions}
      onSubmit={onSubmit}
      onValidityChange={onValidityChange}
      scanSchema={scanSchema}
      {...overrides}
    />
  );

  return {
    ...renderResult,
    ref,
    onSubmit,
    onValidityChange
  };
};

describe('ScanForm', () => {
  it('renders the default scan name, description, and fields', () => {
    renderScanForm();

    expect(screen.getByLabelText('Scan Name')).toHaveValue('censys');

    expect(screen.getByText('Default Censys scan')).toBeInTheDocument();

    expect(
      screen.getByLabelText('Limit enabled organizations')
    ).toBeInTheDocument();

    expect(screen.getByLabelText('Run scan once')).toBeInTheDocument();

    expect(
      screen.getByText('Number of Concurrent Tasks')
    ).toBeInTheDocument();

    expect(
      screen.getByText('This scan allows a maximum of 5 concurrent scans')
    ).toBeInTheDocument();
  });

  it('reports valid initial numeric values to the parent', async () => {
    const { onValidityChange } = renderScanForm();

    await waitFor(() => {
      expect(onValidityChange).toHaveBeenLastCalledWith(true);
    });
  });

  it('submits the expected payload through the exposed ref method', async () => {
    const { ref, onSubmit } = renderScanForm();

    await act(async () => {
      await ref.current?.submit();
    });

    expect(onSubmit).toHaveBeenCalledWith({
      name: 'censys',
      arguments: JSON.stringify({}),
      organizations: [],
      frequency: 1,
      frequencyUnit: 'day',
      is_granular: false,
      is_single_scan: false,
      concurrent_tasks: 1
    });
  });

  it('does not submit when frequency is less than one', async () => {
    const { container, ref, onSubmit, onValidityChange } = renderScanForm();

    const frequencyInput = container.querySelector<HTMLInputElement>(
      '#frequency'
    );

    expect(frequencyInput).not.toBeNull();

    fireEvent.change(frequencyInput!, {
      target: { value: '0' }
    });

    expect(screen.getByText('Positive integer expected')).toBeInTheDocument();

    await waitFor(() => {
      expect(onValidityChange).toHaveBeenLastCalledWith(false);
    });

    await act(async () => {
      await ref.current?.submit();
    });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('does not submit when frequency is not a whole number', async () => {
    const { container, ref, onSubmit } = renderScanForm();

    const frequencyInput = container.querySelector<HTMLInputElement>(
      '#frequency'
    );

    fireEvent.change(frequencyInput!, {
      target: { value: '1.5' }
    });

    expect(screen.getByText('Positive integer expected')).toBeInTheDocument();

    await act(async () => {
      await ref.current?.submit();
    });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('does not submit when concurrent tasks exceeds the scan maximum', async () => {
    const { container, ref, onSubmit, onValidityChange } = renderScanForm();

    const concurrentTasksInput = container.querySelector<HTMLInputElement>(
      '#concurrent_tasks'
    );

    expect(concurrentTasksInput).not.toBeNull();

    fireEvent.change(concurrentTasksInput!, {
      target: { value: '6' }
    });

    expect(
      screen.getByText('Positive integer within range expected')
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(onValidityChange).toHaveBeenLastCalledWith(false);
    });

    await act(async () => {
      await ref.current?.submit();
    });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('allows any positive concurrent-task count when the schema has no maximum', async () => {
    const user = userEvent.setup();

    const { container, ref, onSubmit } = renderScanForm();

    await user.click(screen.getByLabelText('Scan Name'));
    await user.click(screen.getByText('unlimitedScan'));

    expect(
      screen.getByText('This scan allows no limit of concurrent tasks')
    ).toBeInTheDocument();

    const concurrentTasksInput = container.querySelector<HTMLInputElement>(
      '#concurrent_tasks'
    );

    fireEvent.change(concurrentTasksInput!, {
      target: { value: '100' }
    });

    await act(async () => {
      await ref.current?.submit();
    });

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'unlimitedScan',
        concurrent_tasks: 100
      })
    );
  });

  it('shows enabled organizations when granular mode is selected', async () => {
    const user = userEvent.setup();

    renderScanForm();

    await user.click(screen.getByLabelText('Limit enabled organizations'));

    expect(
      screen.getByLabelText('Enabled Organizations')
    ).toBeInTheDocument();
  });

  it('enables a date range and forces the scan to run once', async () => {
    const user = userEvent.setup();

    renderScanForm({
      propValues: {
        ...propValues,
        name: 'vulnScanningSync'
      }
    });

    await user.click(screen.getByLabelText('Scan Name'));
    await user.click(screen.getByText('vulnScanningSync'));

    await user.click(
      screen.getByLabelText('Limit scan to specific date range')
    );

    expect(
      screen.getByText('Start Date (UTC)')
    ).toBeInTheDocument();

    expect(
      screen.getByText('End Date and Time')
    ).toBeInTheDocument();

    expect(screen.getByLabelText('Run scan once')).toBeChecked();

    expect(screen.getByLabelText('Run scan once')).toBeDisabled();

    expect(
      screen.getByText('Must run once while limiting to a date range')
    ).toBeInTheDocument();
  });

  it('does not submit a date range when the start is after the end', async () => {
    const user = userEvent.setup();

    const { container, ref, onSubmit } = renderScanForm();

    await user.click(screen.getByLabelText('Scan Name'));
    await user.click(screen.getByText('vulnScanningSync'));

    await user.click(
      screen.getByLabelText('Limit scan to specific date range')
    );

    const startDateInput = container.querySelector<HTMLInputElement>(
      '#start_datetime'
    );
    const endDateInput = container.querySelector<HTMLInputElement>(
      '#end_datetime'
    );

    expect(startDateInput).not.toBeNull();
    expect(endDateInput).not.toBeNull();

    fireEvent.change(startDateInput!, {
      target: { value: '2026-01-10T00:00' }
    });

    fireEvent.change(endDateInput!, {
      target: { value: '2026-01-09T00:00' }
    });

    await act(async () => {
      await ref.current?.submit();
    });

    expect(
      screen.getByText('Start date must be before end date.')
    ).toBeInTheDocument();

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits UTC ISO date values when a valid date range is used', async () => {
    const user = userEvent.setup();

    const { container, ref, onSubmit } = renderScanForm();

    await user.click(screen.getByLabelText('Scan Name'));
    await user.click(screen.getByText('vulnScanningSync'));

    await user.click(
      screen.getByLabelText('Limit scan to specific date range')
    );

    const startDateInput = container.querySelector<HTMLInputElement>(
      '#start_datetime'
    );
    const endDateInput = container.querySelector<HTMLInputElement>(
      '#end_datetime'
    );

    fireEvent.change(startDateInput!, {
      target: { value: '2026-01-01T00:00' }
    });

    fireEvent.change(endDateInput!, {
      target: { value: '2026-01-02T00:00' }
    });

    await act(async () => {
      await ref.current?.submit();
    });

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'vulnScanningSync',
        is_single_scan: true,
        arguments: JSON.stringify({
          start_datetime: new Date('2026-01-01T00:00').toISOString(),
          end_datetime: new Date('2026-01-02T00:00').toISOString()
        })
      })
    );
  });
});
