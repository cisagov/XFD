import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from 'test-utils';
import userEvent from '@testing-library/user-event';
import { OrganizationForm } from '@/pages/Organizations/OrganizationForm';

// ----- mocks -----
const mockApiGet = vi.fn();
const mockLoggerError = vi.fn();

vi.mock('context', async () => {
  const actualModule = await vi.importActual<any>('context');
  return {
    ...actualModule,
    useAuthContext: () => ({
      apiGet: mockApiGet
    })
  };
});

vi.mock('@/utils/logger', () => ({
  logger: {
    error: (...argumentsList: unknown[]) => mockLoggerError(...argumentsList)
  }
}));

vi.mock('@/constants/endpoints', () => ({
  ENDPOINTS: {
    ORGANIZATIONS_TAGS: '/api/organizations/tags'
  }
}));

vi.mock('@/constants/constants', () => ({
  STATE_OPTIONS: ['Virginia', 'Maryland'],
  STATE_ABBREVIATED_OPTIONS: ['VA', 'MD']
}));

vi.mock('@/pages/Organizations/orgFormStyle', async () => {
  const Dialog = (await import('@mui/material/Dialog')).default;
  return {
    StyledDialog: Dialog
  };
});

type OrganizationLike = {
  id: string;
  name: string;
  acronym: string;
  root_domains: string[];
  ip_blocks: string[];
  is_passive: boolean;
  state_name: string;
};

const getStateSelectCombobox = () => {
  const comboboxes = screen.getAllByRole('combobox');
  const stateCombobox = comboboxes.find(
    (element) => element.getAttribute('id') === 'state_name'
  );

  if (!stateCombobox) {
    throw new Error(
      'State select combobox with id="state_name" was not found.'
    );
  }

  return stateCombobox;
};

const getPassiveModeSwitch = () =>
  screen.getByRole('switch', { name: 'Passive Mode' });

const renderOrganizationForm = async (
  overrides?: Partial<React.ComponentProps<typeof OrganizationForm>>
) => {
  const setOpen = overrides?.setOpen ?? vi.fn();
  const onSubmit = overrides?.onSubmit ?? vi.fn().mockResolvedValue(undefined);

  const Wrapper: React.FC = () => {
    const [chosenTags, setChosenTags] = React.useState<string[]>(
      overrides?.chosenTags ?? []
    );

    return (
      <OrganizationForm
        open={overrides?.open ?? true}
        setOpen={setOpen}
        onSubmit={onSubmit}
        type={overrides?.type ?? 'organization'}
        organization={overrides?.organization}
        parent={overrides?.parent}
        chosenTags={chosenTags}
        setChosenTags={setChosenTags}
      />
    );
  };

  const utils = render(<Wrapper />);

  await waitFor(() => {
    expect(mockApiGet).toHaveBeenCalled();
  });

  return { setOpen, onSubmit, ...utils };
};

const fillRequiredFields = async () => {
  const user = userEvent.setup();

  await user.type(
    screen.getByPlaceholderText("Enter the Organization's Name"),
    'My Organization'
  );

  await user.type(
    screen.getByPlaceholderText('Enter a unique Acronym for the Organization'),
    'MO'
  );

  await user.type(
    screen.getByPlaceholderText('Enter Root Domains, comma separated'),
    'example.com'
  );

  await user.click(getStateSelectCombobox());
  await user.click(screen.getByRole('option', { name: 'Virginia' }));

  return user;
};

describe('OrganizationForm', () => {
  // Create mode shows blank fields by default.
  it('loads empty fields in create mode', async () => {
    mockApiGet.mockResolvedValueOnce([]);

    renderOrganizationForm({ organization: undefined });

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith('/api/organizations/tags');
    });

    expect(screen.getByText('Create New Organization')).toBeInTheDocument();

    expect(
      screen.getByPlaceholderText("Enter the Organization's Name")
    ).toHaveValue('');
    expect(
      screen.getByPlaceholderText('Enter a unique Acronym for the Organization')
    ).toHaveValue('');
    expect(
      screen.getByPlaceholderText('Enter Root Domains, comma separated')
    ).toHaveValue('');
    expect(
      screen.getByPlaceholderText('Enter IP Blocks, comma separated')
    ).toHaveValue('');

    const passiveSwitch = getPassiveModeSwitch();
    expect(passiveSwitch).not.toBeChecked();
  });

  // Providing an organization pre-fills the form (edit-like mode).
  it('loads existing organization values when an organization is provided', async () => {
    mockApiGet.mockResolvedValueOnce([]);

    const existingOrganization: OrganizationLike = {
      id: 'organization-123',
      name: 'Example Org',
      acronym: 'EXO',
      root_domains: ['example.org', 'example.gov'],
      ip_blocks: ['10.0.0.0/8', '192.168.0.0/16'],
      is_passive: true,
      state_name: 'Virginia'
    };

    renderOrganizationForm({ organization: existingOrganization as any });

    expect(screen.getByText('Create New Organization')).toBeInTheDocument();

    expect(
      screen.getByPlaceholderText("Enter the Organization's Name")
    ).toHaveValue('Example Org');
    expect(
      screen.getByPlaceholderText('Enter a unique Acronym for the Organization')
    ).toHaveValue('EXO');
    expect(
      screen.getByPlaceholderText('Enter Root Domains, comma separated')
    ).toHaveValue('example.org, example.gov');
    expect(
      screen.getByPlaceholderText('Enter IP Blocks, comma separated')
    ).toHaveValue('10.0.0.0/8, 192.168.0.0/16');

    const passiveSwitch = getPassiveModeSwitch();
    expect(passiveSwitch).toBeChecked();
  });

  // Empty required fields show errors and prevent submission.
  it('validates required fields and blocks submit', async () => {
    mockApiGet.mockResolvedValueOnce([]);

    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderOrganizationForm({ onSubmit });

    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(
      screen.getByText('Organization Name is required')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Organization Acronym is required')
    ).toBeInTheDocument();
    expect(
      screen.getByText('At least one Root Domain is required')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Organization State is required')
    ).toBeInTheDocument();

    expect(onSubmit).not.toHaveBeenCalled();
  });

  // Submitting valid values sends the expected normalized payload.
  it('submits correct payload on success (split/trim, state abbreviation, tags, passive, parent)', async () => {
    mockApiGet.mockResolvedValueOnce([{ name: 'ExistingTag' }]);

    const setOpen = vi.fn();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const parentOrganization = { id: 'parent-999' } as any;

    renderOrganizationForm({ setOpen, onSubmit, parent: parentOrganization });

    const user = userEvent.setup();

    await user.type(
      screen.getByPlaceholderText("Enter the Organization's Name"),
      'My Organization'
    );
    await user.type(
      screen.getByPlaceholderText(
        'Enter a unique Acronym for the Organization'
      ),
      'MO'
    );
    await user.type(
      screen.getByPlaceholderText('Enter Root Domains, comma separated'),
      'example.com, test.gov  '
    );
    await user.type(
      screen.getByPlaceholderText('Enter IP Blocks, comma separated'),
      '1.1.1.1/32,  2.2.2.0/24'
    );

    await user.click(getStateSelectCombobox());
    await user.click(screen.getByRole('option', { name: 'Virginia' }));

    const tagInput = screen.getByPlaceholderText('Select or add tags');
    await user.type(tagInput, 'AlphaTag{enter}');
    await user.type(tagInput, 'BetaTag{enter}');

    const passiveSwitch = getPassiveModeSwitch();
    await user.click(passiveSwitch);
    expect(passiveSwitch).toBeChecked();

    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    expect(onSubmit).toHaveBeenCalledWith({
      root_domains: ['example.com', 'test.gov'],
      ip_blocks: ['1.1.1.1/32', '2.2.2.0/24'],
      name: 'My Organization',
      state_name: 'Virginia',
      state: 'VA',
      is_passive: true,
      tags: [{ name: 'AlphaTag' }, { name: 'BetaTag' }],
      acronym: 'MO',
      parent: 'parent-999'
    });

    expect(setOpen).toHaveBeenCalledWith(false);
  });

  // In create mode, the form resets values after a successful submit.
  it('resets fields after successful submit in create mode (original behavior)', async () => {
    mockApiGet.mockResolvedValueOnce([]);

    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderOrganizationForm({ onSubmit, organization: undefined });

    const user = await fillRequiredFields();

    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    expect(
      screen.getByPlaceholderText("Enter the Organization's Name")
    ).toHaveValue('');
    expect(
      screen.getByPlaceholderText('Enter a unique Acronym for the Organization')
    ).toHaveValue('');
    expect(
      screen.getByPlaceholderText('Enter Root Domains, comma separated')
    ).toHaveValue('');
  });

  // In edit-like mode, the form does not reset values after submit.
  it('does not reset fields after submit when organization is provided (edit-like behavior)', async () => {
    mockApiGet.mockResolvedValueOnce([]);

    const existingOrganization: OrganizationLike = {
      id: 'organization-123',
      name: 'Example Org',
      acronym: 'EXO',
      root_domains: ['example.org'],
      ip_blocks: [],
      is_passive: false,
      state_name: 'Virginia'
    };

    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderOrganizationForm({
      onSubmit,
      organization: existingOrganization as any
    });

    const user = userEvent.setup();

    await user.clear(
      screen.getByPlaceholderText("Enter the Organization's Name")
    );
    await user.type(
      screen.getByPlaceholderText("Enter the Organization's Name"),
      'Updated Org'
    );

    await user.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    expect(
      screen.getByPlaceholderText("Enter the Organization's Name")
    ).toHaveValue('Updated Org');
  });

  // Cancel closes the dialog without submitting.
  it('clicking Cancel calls setOpen(false)', async () => {
    mockApiGet.mockResolvedValueOnce([]);

    const user = userEvent.setup();
    const setOpen = vi.fn();

    renderOrganizationForm({ setOpen });

    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(setOpen).toHaveBeenCalledWith(false);
  });

  it('fetches tags on mount and logs error if tag fetch fails', async () => {
    mockApiGet.mockRejectedValueOnce(new Error('tag fetch failed'));

    renderOrganizationForm();

    await waitFor(() => {
      expect(mockLoggerError).toHaveBeenCalled();
    });
  });
});
