# Integration Test Templates

Templates for integration tests that test multiple components working together in the XFD frontend application.

> **📝 Important Note**: The XFD codebase currently has mixed import patterns for test-utils. These templates use the recommended pattern (`import { render, screen } from 'test-utils'`), but you may see existing tests using different patterns. For new tests, use the patterns shown in these templates.

## Table of Contents

- [Page Integration Template](#page-integration-template)
- [Form Flow Integration Template](#form-flow-integration-template)
- [API Integration Template](#api-integration-template)
- [Authentication Flow Template](#authentication-flow-template)
- [Data Flow Integration Template](#data-flow-integration-template)
- [Navigation Integration Template](#navigation-integration-template)

---

## Page Integration Template

Use this for testing complete page components with their full functionality.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { testUser, testOrganization } from 'test-utils';
import { YourPage } from '../../pages/YourPage';

// Mock API calls
vi.mock('../../api/endpoints', () => ({
  fetchPageData: vi.fn(),
  updatePageData: vi.fn(),
  deleteItem: vi.fn()
}));

// Mock child components if needed
vi.mock('../../components/DataTable', () => ({
  DataTable: ({ data, onEdit, onDelete }: any) => (
    <div data-testid="data-table">
      {data.map((item: any) => (
        <div key={item.id} data-testid={`item-${item.id}`}>
          <span>{item.name}</span>
          <button onClick={() => onEdit(item)} data-testid={`edit-${item.id}`}>
            Edit
          </button>
          <button onClick={() => onDelete(item.id)} data-testid={`delete-${item.id}`}>
            Delete
          </button>
        </div>
      ))}
    </div>
  )
}));

import { fetchPageData, updatePageData, deleteItem } from '../../api/endpoints';
const mockFetchPageData = vi.mocked(fetchPageData);
const mockUpdatePageData = vi.mocked(updatePageData);
const mockDeleteItem = vi.mocked(deleteItem);

const mockPageData = [
  { id: 1, name: 'Item 1', status: 'active' },
  { id: 2, name: 'Item 2', status: 'inactive' },
  { id: 3, name: 'Item 3', status: 'active' }
];

describe('YourPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchPageData.mockResolvedValue({ data: mockPageData });
  });

  const renderPage = (route = '/your-page') => {
    return render(
      <MemoryRouter initialEntries={[route]}>
        <YourPage />
      </MemoryRouter>,
      {
        initialAuthState: {
          isAuthenticated: true,
          user: testUser,
          currentOrganization: testOrganization
        }
      }
    );
  };

  it('renders page with all components', async () => {
    renderPage();
    
    // Check for loading state initially
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.queryByTestId('loading-indicator')).not.toBeInTheDocument();
    });
    
    // Check all main components are rendered
    expect(screen.getByTestId('page-header')).toBeInTheDocument();
    expect(screen.getByTestId('filter-controls')).toBeInTheDocument();
    expect(screen.getByTestId('data-table')).toBeInTheDocument();
    expect(screen.getByTestId('pagination')).toBeInTheDocument();
  });

  it('loads and displays data correctly', async () => {
    renderPage();
    
    await waitFor(() => {
      expect(mockFetchPageData).toHaveBeenCalledWith({
        organizationId: testOrganization.id,
        filters: {},
        page: 1,
        pageSize: 10
      });
    });
    
    // Check data is displayed
    expect(screen.getByTestId('item-1')).toHaveTextContent('Item 1');
    expect(screen.getByTestId('item-2')).toHaveTextContent('Item 2');
    expect(screen.getByTestId('item-3')).toHaveTextContent('Item 3');
  });

  it('handles filtering correctly', async () => {
    renderPage();
    
    await waitFor(() => {
      expect(screen.getByTestId('data-table')).toBeInTheDocument();
    });
    
    // Apply status filter
    const statusFilter = screen.getByTestId('status-filter');
    fireEvent.change(statusFilter, { target: { value: 'active' } });
    
    // Should trigger new API call with filter
    await waitFor(() => {
      expect(mockFetchPageData).toHaveBeenCalledWith({
        organizationId: testOrganization.id,
        filters: { status: 'active' },
        page: 1,
        pageSize: 10
      });
    });
  });

  it('handles pagination correctly', async () => {
    renderPage();
    
    await waitFor(() => {
      expect(screen.getByTestId('pagination')).toBeInTheDocument();
    });
    
    // Click next page
    const nextButton = screen.getByTestId('next-page');
    fireEvent.click(nextButton);
    
    await waitFor(() => {
      expect(mockFetchPageData).toHaveBeenCalledWith({
        organizationId: testOrganization.id,
        filters: {},
        page: 2,
        pageSize: 10
      });
    });
  });

  it('handles edit functionality end-to-end', async () => {
    renderPage();
    
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toBeInTheDocument();
    });
    
    // Click edit button
    const editButton = screen.getByTestId('edit-1');
    fireEvent.click(editButton);
    
    // Edit dialog should open
    await waitFor(() => {
      expect(screen.getByTestId('edit-dialog')).toBeInTheDocument();
    });
    
    // Update the item name
    const nameInput = screen.getByTestId('item-name-input');
    fireEvent.change(nameInput, { target: { value: 'Updated Item 1' } });
    
    // Save changes
    mockUpdatePageData.mockResolvedValue({ data: { ...mockPageData[0], name: 'Updated Item 1' } });
    const saveButton = screen.getByTestId('save-button');
    fireEvent.click(saveButton);
    
    // Should call API and close dialog
    await waitFor(() => {
      expect(mockUpdatePageData).toHaveBeenCalledWith(1, { name: 'Updated Item 1' });
      expect(screen.queryByTestId('edit-dialog')).not.toBeInTheDocument();
    });
  });

  it('handles delete functionality end-to-end', async () => {
    renderPage();
    
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toBeInTheDocument();
    });
    
    // Click delete button
    const deleteButton = screen.getByTestId('delete-1');
    fireEvent.click(deleteButton);
    
    // Confirmation dialog should open
    await waitFor(() => {
      expect(screen.getByTestId('delete-confirmation')).toBeInTheDocument();
    });
    
    // Confirm deletion
    mockDeleteItem.mockResolvedValue({ status: 204 });
    const confirmButton = screen.getByTestId('confirm-delete');
    fireEvent.click(confirmButton);
    
    // Should call API and refresh data
    await waitFor(() => {
      expect(mockDeleteItem).toHaveBeenCalledWith(1);
    });
  });

  it('handles error states correctly', async () => {
    const error = new Error('Failed to load data');
    mockFetchPageData.mockRejectedValue(error);
    
    renderPage();
    
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
      expect(screen.getByTestId('error-message')).toHaveTextContent('Failed to load data');
    });
    
    // Should show retry button
    expect(screen.getByTestId('retry-button')).toBeInTheDocument();
    
    // Retry should work
    mockFetchPageData.mockResolvedValue({ data: mockPageData });
    const retryButton = screen.getByTestId('retry-button');
    fireEvent.click(retryButton);
    
    await waitFor(() => {
      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
      expect(screen.getByTestId('data-table')).toBeInTheDocument();
    });
  });

  it('handles unauthorized access correctly', async () => {
    render(
      <MemoryRouter initialEntries={['/your-page']}>
        <YourPage />
      </MemoryRouter>,
      {
        initialAuthState: {
          isAuthenticated: false,
          user: null,
          currentOrganization: null
        }
      }
    );
    
    // Should redirect to login or show unauthorized message
    await waitFor(() => {
      expect(screen.getByTestId('unauthorized-message')).toBeInTheDocument();
    });
  });
});
```

---

## Form Flow Integration Template

Use this for testing complex forms with multiple steps or validation.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { testUser } from 'test-utils';
import { YourFormFlow } from '../../components/YourFormFlow';

// Mock API
vi.mock('../../api/form-endpoints', () => ({
  validateStep: vi.fn(),
  submitForm: vi.fn(),
  saveAsDraft: vi.fn()
}));

import { validateStep, submitForm, saveAsDraft } from '../../api/form-endpoints';
const mockValidateStep = vi.mocked(validateStep);
const mockSubmitForm = vi.mocked(submitForm);
const mockSaveAsDraft = vi.mocked(saveAsDraft);

describe('YourFormFlow Integration', () => {
  const user = userEvent.setup();
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderFormFlow = (props = {}) => {
    return render(
      <YourFormFlow
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        {...props}
      />,
      {
        initialAuthState: {
          isAuthenticated: true,
          user: testUser
        }
      }
    );
  };

  it('renders first step initially', () => {
    renderFormFlow();
    
    expect(screen.getByTestId('form-step-1')).toBeInTheDocument();
    expect(screen.getByTestId('step-indicator')).toHaveTextContent('Step 1 of 3');
    expect(screen.queryByTestId('form-step-2')).not.toBeInTheDocument();
    expect(screen.queryByTestId('form-step-3')).not.toBeInTheDocument();
  });

  it('progresses through all steps correctly', async () => {
    mockValidateStep.mockResolvedValue({ isValid: true });
    
    renderFormFlow();
    
    // Fill out step 1
    await user.type(screen.getByTestId('first-name'), 'John');
    await user.type(screen.getByTestId('last-name'), 'Doe');
    await user.type(screen.getByTestId('email'), 'john.doe@example.com');
    
    // Go to step 2
    await user.click(screen.getByTestId('next-step-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('form-step-2')).toBeInTheDocument();
      expect(screen.getByTestId('step-indicator')).toHaveTextContent('Step 2 of 3');
    });
    
    // Fill out step 2
    await user.type(screen.getByTestId('company-name'), 'ACME Corp');
    await user.selectOptions(screen.getByTestId('industry-select'), 'technology');
    
    // Go to step 3
    await user.click(screen.getByTestId('next-step-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('form-step-3')).toBeInTheDocument();
      expect(screen.getByTestId('step-indicator')).toHaveTextContent('Step 3 of 3');
    });
  });

  it('validates each step before progression', async () => {
    renderFormFlow();
    
    // Try to go to next step without filling required fields
    await user.click(screen.getByTestId('next-step-button'));
    
    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByTestId('first-name-error')).toHaveTextContent('First name is required');
      expect(screen.getByTestId('email-error')).toHaveTextContent('Email is required');
    });
    
    // Should still be on step 1
    expect(screen.getByTestId('form-step-1')).toBeInTheDocument();
    expect(screen.getByTestId('step-indicator')).toHaveTextContent('Step 1 of 3');
  });

  it('handles server-side validation errors', async () => {
    mockValidateStep.mockRejectedValue({
      errors: {
        email: 'Email already exists'
      }
    });
    
    renderFormFlow();
    
    // Fill out form
    await user.type(screen.getByTestId('first-name'), 'John');
    await user.type(screen.getByTestId('last-name'), 'Doe');
    await user.type(screen.getByTestId('email'), 'existing@example.com');
    
    // Try to proceed
    await user.click(screen.getByTestId('next-step-button'));
    
    // Should show server validation error
    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toHaveTextContent('Email already exists');
    });
    
    expect(mockValidateStep).toHaveBeenCalledWith(1, {
      firstName: 'John',
      lastName: 'Doe',
      email: 'existing@example.com'
    });
  });

  it('allows going back to previous steps', async () => {
    mockValidateStep.mockResolvedValue({ isValid: true });
    
    renderFormFlow();
    
    // Fill and complete step 1
    await user.type(screen.getByTestId('first-name'), 'John');
    await user.type(screen.getByTestId('last-name'), 'Doe');
    await user.type(screen.getByTestId('email'), 'john.doe@example.com');
    await user.click(screen.getByTestId('next-step-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('form-step-2')).toBeInTheDocument();
    });
    
    // Go back to step 1
    await user.click(screen.getByTestId('previous-step-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('form-step-1')).toBeInTheDocument();
    });
    
    // Form should retain previous values
    expect(screen.getByTestId('first-name')).toHaveValue('John');
    expect(screen.getByTestId('last-name')).toHaveValue('Doe');
    expect(screen.getByTestId('email')).toHaveValue('john.doe@example.com');
  });

  it('saves draft automatically', async () => {
    mockSaveAsDraft.mockResolvedValue({ id: 'draft-123' });
    
    renderFormFlow();
    
    // Fill out some form data
    await user.type(screen.getByTestId('first-name'), 'John');
    await user.type(screen.getByTestId('last-name'), 'Doe');
    
    // Wait for auto-save (debounced)
    await waitFor(() => {
      expect(mockSaveAsDraft).toHaveBeenCalledWith({
        firstName: 'John',
        lastName: 'Doe',
        email: ''
      });
    }, { timeout: 3000 });
    
    // Should show draft saved indicator
    expect(screen.getByTestId('draft-saved-indicator')).toBeInTheDocument();
  });

  it('submits complete form successfully', async () => {
    mockValidateStep.mockResolvedValue({ isValid: true });
    mockSubmitForm.mockResolvedValue({ id: 'form-123' });
    const mockOnSubmit = vi.fn();
    
    renderFormFlow({ onSubmit: mockOnSubmit });
    
    // Complete step 1
    await user.type(screen.getByTestId('first-name'), 'John');
    await user.type(screen.getByTestId('last-name'), 'Doe');
    await user.type(screen.getByTestId('email'), 'john.doe@example.com');
    await user.click(screen.getByTestId('next-step-button'));
    
    await waitFor(() => expect(screen.getByTestId('form-step-2')).toBeInTheDocument());
    
    // Complete step 2
    await user.type(screen.getByTestId('company-name'), 'ACME Corp');
    await user.selectOptions(screen.getByTestId('industry-select'), 'technology');
    await user.click(screen.getByTestId('next-step-button'));
    
    await waitFor(() => expect(screen.getByTestId('form-step-3')).toBeInTheDocument());
    
    // Complete step 3 and submit
    await user.check(screen.getByTestId('terms-checkbox'));
    await user.click(screen.getByTestId('submit-button'));
    
    // Should show loading state
    expect(screen.getByTestId('submit-loading')).toBeInTheDocument();
    
    // Should submit form
    await waitFor(() => {
      expect(mockSubmitForm).toHaveBeenCalledWith({
        firstName: 'John',
        lastName: 'Doe',
        email: 'john.doe@example.com',
        companyName: 'ACME Corp',
        industry: 'technology',
        acceptedTerms: true
      });
    });
    
    // Should call onSubmit callback
    expect(mockOnSubmit).toHaveBeenCalledWith({ id: 'form-123' });
  });

  it('handles form submission errors', async () => {
    mockValidateStep.mockResolvedValue({ isValid: true });
    mockSubmitForm.mockRejectedValue(new Error('Submission failed'));
    
    renderFormFlow();
    
    // Navigate to final step (simplified)
    // ... fill form steps ...
    
    // Submit form
    await user.click(screen.getByTestId('submit-button'));
    
    // Should show error
    await waitFor(() => {
      expect(screen.getByTestId('submission-error')).toHaveTextContent('Submission failed');
    });
    
    // Submit button should be re-enabled
    expect(screen.getByTestId('submit-button')).not.toBeDisabled();
  });

  it('handles form cancellation', async () => {
    const mockOnCancel = vi.fn();
    
    renderFormFlow({ onCancel: mockOnCancel });
    
    // Fill some data
    await user.type(screen.getByTestId('first-name'), 'John');
    
    // Click cancel
    await user.click(screen.getByTestId('cancel-button'));
    
    // Should show confirmation dialog
    await waitFor(() => {
      expect(screen.getByTestId('cancel-confirmation')).toBeInTheDocument();
    });
    
    // Confirm cancellation
    await user.click(screen.getByTestId('confirm-cancel'));
    
    expect(mockOnCancel).toHaveBeenCalled();
  });
});
```

---

## API Integration Template

Use this for testing components that heavily interact with APIs.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { testUser, testOrganization } from 'test-utils';
import { YourAPIComponent } from '../../components/YourAPIComponent';

// Setup MSW server for API mocking
const server = setupServer(
  rest.get('/api/items', (req, res, ctx) => {
    return res(
      ctx.json({
        data: [
          { id: 1, name: 'Item 1', status: 'active' },
          { id: 2, name: 'Item 2', status: 'inactive' }
        ],
        pagination: { total: 2, page: 1, pageSize: 10 }
      })
    );
  }),
  
  rest.post('/api/items', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({ id: 3, name: 'New Item', status: 'active' })
    );
  }),
  
  rest.put('/api/items/:id', (req, res, ctx) => {
    const { id } = req.params;
    return res(
      ctx.json({ id: Number(id), name: 'Updated Item', status: 'active' })
    );
  }),
  
  rest.delete('/api/items/:id', (req, res, ctx) => {
    return res(ctx.status(204));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('YourAPIComponent Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (props = {}) => {
    return render(
      <YourAPIComponent {...props} />,
      {
        initialAuthState: {
          isAuthenticated: true,
          user: testUser,
          currentOrganization: testOrganization
        }
      }
    );
  };

  it('loads and displays data from API', async () => {
    renderComponent();
    
    // Should show loading initially
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    
    // Should load and display data
    await waitFor(() => {
      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
    });
    
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    // Override server response to return error
    server.use(
      rest.get('/api/items', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ message: 'Server error' }));
      })
    );
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent('Server error');
    });
  });

  it('creates new items via API', async () => {
    renderComponent();
    
    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
    });
    
    // Click create button
    fireEvent.click(screen.getByTestId('create-item-button'));
    
    // Fill form
    fireEvent.change(screen.getByTestId('item-name-input'), {
      target: { value: 'New Item' }
    });
    
    // Submit
    fireEvent.click(screen.getByTestId('submit-button'));
    
    // Should show success message
    await waitFor(() => {
      expect(screen.getByTestId('success-message')).toBeInTheDocument();
    });
  });

  it('updates existing items via API', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
    });
    
    // Click edit button for first item
    fireEvent.click(screen.getByTestId('edit-item-1'));
    
    // Update name
    const nameInput = screen.getByTestId('item-name-input');
    fireEvent.change(nameInput, { target: { value: 'Updated Item' } });
    
    // Submit update
    fireEvent.click(screen.getByTestId('update-button'));
    
    await waitFor(() => {
      expect(screen.getByText('Updated Item')).toBeInTheDocument();
    });
  });

  it('deletes items via API', async () => {
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
    });
    
    // Click delete button
    fireEvent.click(screen.getByTestId('delete-item-1'));
    
    // Confirm deletion
    fireEvent.click(screen.getByTestId('confirm-delete'));
    
    await waitFor(() => {
      expect(screen.queryByText('Item 1')).not.toBeInTheDocument();
    });
  });

  it('handles network errors', async () => {
    // Simulate network error
    server.use(
      rest.get('/api/items', (req, res) => {
        return res.networkError('Network error');
      })
    );
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByTestId('network-error')).toBeInTheDocument();
    });
  });

  it('handles concurrent API requests correctly', async () => {
    let resolveFirstRequest: (value: any) => void;
    let resolveSecondRequest: (value: any) => void;
    
    server.use(
      rest.get('/api/items', (req, res, ctx) => {
        const page = req.url.searchParams.get('page');
        if (page === '1') {
          return new Promise(resolve => { resolveFirstRequest = resolve; });
        } else {
          return new Promise(resolve => { resolveSecondRequest = resolve; });
        }
      })
    );
    
    renderComponent();
    
    // Trigger page change while first request is pending
    fireEvent.click(screen.getByTestId('next-page'));
    
    // Resolve second request first
    resolveSecondRequest!({
      json: () => ({ data: [{ id: 3, name: 'Page 2 Item' }] })
    });
    
    // Then resolve first request (should be ignored)
    resolveFirstRequest!({
      json: () => ({ data: [{ id: 1, name: 'Page 1 Item' }] })
    });
    
    await waitFor(() => {
      expect(screen.getByText('Page 2 Item')).toBeInTheDocument();
      expect(screen.queryByText('Page 1 Item')).not.toBeInTheDocument();
    });
  });
});
```

---

## Authentication Flow Template

Use this for testing authentication-related components and flows.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import { testUser, testOrganization } from 'test-utils';
import { AuthenticatedApp } from '../../components/AuthenticatedApp';

// Mock authentication service
vi.mock('../../services/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  refreshToken: vi.fn(),
  getCurrentUser: vi.fn()
}));

// Mock route components
vi.mock('../../pages/Dashboard', () => ({
  Dashboard: () => <div data-testid="dashboard">Dashboard Page</div>
}));

vi.mock('../../pages/Profile', () => ({
  Profile: () => <div data-testid="profile">Profile Page</div>
}));

import { login, logout, refreshToken, getCurrentUser } from '../../services/auth';
const mockLogin = vi.mocked(login);
const mockLogout = vi.mocked(logout);
const mockRefreshToken = vi.mocked(refreshToken);
const mockGetCurrentUser = vi.mocked(getCurrentUser);

describe('Authentication Flow Integration', () => {
  const user = userEvent.setup();
  
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  const renderApp = (initialRoute = '/') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <AuthenticatedApp />
      </MemoryRouter>
    );
  };

  it('redirects to login when not authenticated', () => {
    renderApp('/dashboard');
    
    expect(screen.getByTestId('login-form')).toBeInTheDocument();
    expect(screen.queryByTestId('dashboard')).not.toBeInTheDocument();
  });

  it('shows dashboard when authenticated', () => {
    renderApp('/', {
      initialAuthState: {
        isAuthenticated: true,
        user: testUser,
        currentOrganization: testOrganization
      }
    });
    
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    expect(screen.queryByTestId('login-form')).not.toBeInTheDocument();
  });

  it('handles login flow completely', async () => {
    const loginResponse = {
      user: testUser,
      token: 'auth-token',
      refreshToken: 'refresh-token'
    };
    mockLogin.mockResolvedValue(loginResponse);
    
    renderApp('/dashboard');
    
    // Should show login form
    expect(screen.getByTestId('login-form')).toBeInTheDocument();
    
    // Fill login form
    await user.type(screen.getByTestId('email-input'), 'test@example.com');
    await user.type(screen.getByTestId('password-input'), 'password123');
    
    // Submit login
    await user.click(screen.getByTestId('login-button'));
    
    // Should show loading state
    expect(screen.getByTestId('login-loading')).toBeInTheDocument();
    
    // Should redirect to dashboard after successful login
    await waitFor(() => {
      expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    });
    
    expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
  });

  it('handles login errors', async () => {
    mockLogin.mockRejectedValue(new Error('Invalid credentials'));
    
    renderApp();
    
    await user.type(screen.getByTestId('email-input'), 'wrong@example.com');
    await user.type(screen.getByTestId('password-input'), 'wrongpassword');
    await user.click(screen.getByTestId('login-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toHaveTextContent('Invalid credentials');
    });
    
    // Should still show login form
    expect(screen.getByTestId('login-form')).toBeInTheDocument();
  });

  it('handles logout flow', async () => {
    mockLogout.mockResolvedValue(undefined);
    
    renderApp('/', {
      initialAuthState: {
        isAuthenticated: true,
        user: testUser,
        currentOrganization: testOrganization
      }
    });
    
    // Should show authenticated content
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    
    // Click logout
    await user.click(screen.getByTestId('logout-button'));
    
    await waitFor(() => {
      expect(screen.getByTestId('login-form')).toBeInTheDocument();
    });
    
    expect(mockLogout).toHaveBeenCalled();
  });

  it('handles token refresh automatically', async () => {
    const newToken = 'new-auth-token';
    mockRefreshToken.mockResolvedValue({ token: newToken });
    
    // Simulate expired token scenario
    localStorage.setItem('authToken', 'expired-token');
    localStorage.setItem('refreshToken', 'valid-refresh-token');
    
    renderApp('/dashboard', {
      initialAuthState: {
        isAuthenticated: true,
        user: testUser,
        currentOrganization: testOrganization
      }
    });
    
    // Should automatically refresh token
    await waitFor(() => {
      expect(mockRefreshToken).toHaveBeenCalledWith('valid-refresh-token');
    });
    
    // Should update localStorage with new token
    expect(localStorage.getItem('authToken')).toBe(newToken);
  });

  it('handles token refresh failure', async () => {
    mockRefreshToken.mockRejectedValue(new Error('Refresh failed'));
    
    localStorage.setItem('authToken', 'expired-token');
    localStorage.setItem('refreshToken', 'invalid-refresh-token');
    
    renderApp('/dashboard', {
      initialAuthState: {
        isAuthenticated: true,
        user: testUser,
        currentOrganization: testOrganization
      }
    });
    
    // Should redirect to login when refresh fails
    await waitFor(() => {
      expect(screen.getByTestId('login-form')).toBeInTheDocument();
    });
    
    // Should clear tokens from storage
    expect(localStorage.getItem('authToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });

  it('handles organization switching', async () => {
    const newOrg = { ...testOrganization, id: '2', name: 'New Organization' };
    
    renderApp('/', {
      initialAuthState: {
        isAuthenticated: true,
        user: { ...testUser, organizations: [testOrganization, newOrg] },
        currentOrganization: testOrganization
      }
    });
    
    // Open organization selector
    await user.click(screen.getByTestId('organization-selector'));
    
    // Select new organization
    await user.click(screen.getByTestId('org-option-2'));
    
    // Should update current organization
    await waitFor(() => {
      expect(screen.getByTestId('current-org-display')).toHaveTextContent('New Organization');
    });
  });

  it('preserves route after login', async () => {
    const loginResponse = {
      user: testUser,
      token: 'auth-token',
      refreshToken: 'refresh-token'
    };
    mockLogin.mockResolvedValue(loginResponse);
    
    // Try to access protected route
    renderApp('/profile');
    
    // Should redirect to login with return URL
    expect(screen.getByTestId('login-form')).toBeInTheDocument();
    
    // Complete login
    await user.type(screen.getByTestId('email-input'), 'test@example.com');
    await user.type(screen.getByTestId('password-input'), 'password123');
    await user.click(screen.getByTestId('login-button'));
    
    // Should redirect back to original route
    await waitFor(() => {
      expect(screen.getByTestId('profile')).toBeInTheDocument();
    });
  });
});
```

---

## Data Flow Integration Template

Use this for testing data flow between multiple components.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { DataFlowContainer } from '../../containers/DataFlowContainer';

// Mock child components
vi.mock('../../components/DataProvider', () => ({
  DataProvider: ({ children, onDataChange }: any) => {
    const [data, setData] = React.useState([]);
    
    React.useEffect(() => {
      // Simulate data loading
      setTimeout(() => {
        const mockData = [
          { id: 1, name: 'Item 1', category: 'A' },
          { id: 2, name: 'Item 2', category: 'B' }
        ];
        setData(mockData);
        onDataChange(mockData);
      }, 100);
    }, []);
    
    return (
      <div data-testid="data-provider">
        {children}
      </div>
    );
  }
}));

vi.mock('../../components/DataFilter', () => ({
  DataFilter: ({ onFilterChange }: any) => (
    <div data-testid="data-filter">
      <select 
        data-testid="category-filter" 
        onChange={(e) => onFilterChange({ category: e.target.value })}
      >
        <option value="">All</option>
        <option value="A">Category A</option>
        <option value="B">Category B</option>
      </select>
    </div>
  )
}));

vi.mock('../../components/DataList', () => ({
  DataList: ({ data, onItemSelect }: any) => (
    <div data-testid="data-list">
      {data.map((item: any) => (
        <div 
          key={item.id} 
          data-testid={`item-${item.id}`}
          onClick={() => onItemSelect(item)}
        >
          {item.name} - {item.category}
        </div>
      ))}
    </div>
  )
}));

vi.mock('../../components/DataDetails', () => ({
  DataDetails: ({ selectedItem, onUpdate }: any) => (
    <div data-testid="data-details">
      {selectedItem ? (
        <div>
          <div data-testid="selected-item-name">{selectedItem.name}</div>
          <button 
            data-testid="update-item"
            onClick={() => onUpdate({ ...selectedItem, name: 'Updated Name' })}
          >
            Update
          </button>
        </div>
      ) : (
        <div data-testid="no-selection">No item selected</div>
      )}
    </div>
  )
}));

describe('Data Flow Integration', () => {
  const user = userEvent.setup();
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and displays data correctly', async () => {
    render(<DataFlowContainer />);
    
    // Initially should show loading or empty state
    expect(screen.getByTestId('data-provider')).toBeInTheDocument();
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toBeInTheDocument();
      expect(screen.getByTestId('item-2')).toBeInTheDocument();
    });
    
    expect(screen.getByTestId('item-1')).toHaveTextContent('Item 1 - A');
    expect(screen.getByTestId('item-2')).toHaveTextContent('Item 2 - B');
  });

  it('filters data correctly', async () => {
    render(<DataFlowContainer />);
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toBeInTheDocument();
    });
    
    // Apply filter
    const categoryFilter = screen.getByTestId('category-filter');
    await user.selectOptions(categoryFilter, 'A');
    
    // Should only show items from category A
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toBeInTheDocument();
      expect(screen.queryByTestId('item-2')).not.toBeInTheDocument();
    });
  });

  it('handles item selection correctly', async () => {
    render(<DataFlowContainer />);
    
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toBeInTheDocument();
    });
    
    // Select an item
    await user.click(screen.getByTestId('item-1'));
    
    // Should show item details
    await waitFor(() => {
      expect(screen.getByTestId('selected-item-name')).toHaveTextContent('Item 1');
    });
  });

  it('propagates updates correctly', async () => {
    render(<DataFlowContainer />);
    
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toBeInTheDocument();
    });
    
    // Select and update an item
    await user.click(screen.getByTestId('item-1'));
    
    await waitFor(() => {
      expect(screen.getByTestId('update-item')).toBeInTheDocument();
    });
    
    await user.click(screen.getByTestId('update-item'));
    
    // Should update the item in the list
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toHaveTextContent('Updated Name');
    });
    
    // Should update the details view
    expect(screen.getByTestId('selected-item-name')).toHaveTextContent('Updated Name');
  });

  it('handles complex data flow scenarios', async () => {
    render(<DataFlowContainer />);
    
    await waitFor(() => {
      expect(screen.getAllByTestId(/^item-\d+$/)).toHaveLength(2);
    });
    
    // 1. Apply filter
    await user.selectOptions(screen.getByTestId('category-filter'), 'A');
    
    await waitFor(() => {
      expect(screen.getAllByTestId(/^item-\d+$/)).toHaveLength(1);
    });
    
    // 2. Select filtered item
    await user.click(screen.getByTestId('item-1'));
    
    // 3. Update the item
    await user.click(screen.getByTestId('update-item'));
    
    // 4. Clear filter to show all items
    await user.selectOptions(screen.getByTestId('category-filter'), '');
    
    // Should show both items with the update applied
    await waitFor(() => {
      expect(screen.getAllByTestId(/^item-\d+$/)).toHaveLength(2);
      expect(screen.getByTestId('item-1')).toHaveTextContent('Updated Name');
    });
  });

  it('maintains state consistency across operations', async () => {
    render(<DataFlowContainer />);
    
    await waitFor(() => {
      expect(screen.getByTestId('item-1')).toBeInTheDocument();
    });
    
    // Perform multiple operations
    await user.click(screen.getByTestId('item-1')); // Select item 1
    await user.click(screen.getByTestId('update-item')); // Update item 1
    await user.click(screen.getByTestId('item-2')); // Select item 2
    
    // Verify state is consistent
    expect(screen.getByTestId('selected-item-name')).toHaveTextContent('Item 2');
    expect(screen.getByTestId('item-1')).toHaveTextContent('Updated Name');
    expect(screen.getByTestId('item-2')).toHaveTextContent('Item 2');
  });
});
```

---

## Navigation Integration Template

Use this for testing navigation and routing behavior.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import { testUser, testOrganization } from 'test-utils';
import { AppWithNavigation } from '../../components/AppWithNavigation';

// Mock page components
vi.mock('../../pages/Dashboard', () => ({
  Dashboard: () => <div data-testid="dashboard-page">Dashboard</div>
}));

vi.mock('../../pages/Users', () => ({
  Users: () => <div data-testid="users-page">Users</div>
}));

vi.mock('../../pages/Settings', () => ({
  Settings: () => <div data-testid="settings-page">Settings</div>
}));

vi.mock('../../pages/Profile', () => ({
  Profile: () => <div data-testid="profile-page">Profile</div>
}));

describe('Navigation Integration', () => {
  const user = userEvent.setup();
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderApp = (initialRoute = '/') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <AppWithNavigation />
      </MemoryRouter>,
      {
        initialAuthState: {
          isAuthenticated: true,
          user: testUser,
          currentOrganization: testOrganization
        }
      }
    );
  };

  it('renders navigation and default route', () => {
    renderApp('/');
    
    expect(screen.getByTestId('main-navigation')).toBeInTheDocument();
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
  });

  it('navigates between pages correctly', async () => {
    renderApp('/');
    
    // Start on dashboard
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    
    // Navigate to users
    await user.click(screen.getByTestId('nav-users'));
    
    await waitFor(() => {
      expect(screen.getByTestId('users-page')).toBeInTheDocument();
      expect(screen.queryByTestId('dashboard-page')).not.toBeInTheDocument();
    });
    
    // Navigate to settings
    await user.click(screen.getByTestId('nav-settings'));
    
    await waitFor(() => {
      expect(screen.getByTestId('settings-page')).toBeInTheDocument();
      expect(screen.queryByTestId('users-page')).not.toBeInTheDocument();
    });
  });

  it('highlights active navigation item', async () => {
    renderApp('/users');
    
    const usersNavItem = screen.getByTestId('nav-users');
    const dashboardNavItem = screen.getByTestId('nav-dashboard');
    
    expect(usersNavItem).toHaveClass('active');
    expect(dashboardNavItem).not.toHaveClass('active');
    
    // Navigate to dashboard
    await user.click(dashboardNavItem);
    
    await waitFor(() => {
      expect(dashboardNavItem).toHaveClass('active');
      expect(usersNavItem).not.toHaveClass('active');
    });
  });

  it('handles direct URL navigation', () => {
    renderApp('/settings');
    
    expect(screen.getByTestId('settings-page')).toBeInTheDocument();
    expect(screen.getByTestId('nav-settings')).toHaveClass('active');
  });

  it('handles invalid routes', () => {
    renderApp('/invalid-route');
    
    expect(screen.getByTestId('not-found-page')).toBeInTheDocument();
  });

  it('handles back/forward browser navigation', async () => {
    const { container } = renderApp('/');
    
    // Navigate to users
    await user.click(screen.getByTestId('nav-users'));
    await waitFor(() => expect(screen.getByTestId('users-page')).toBeInTheDocument());
    
    // Navigate to settings
    await user.click(screen.getByTestId('nav-settings'));
    await waitFor(() => expect(screen.getByTestId('settings-page')).toBeInTheDocument());
    
    // Simulate browser back
    window.history.back();
    
    await waitFor(() => {
      expect(screen.getByTestId('users-page')).toBeInTheDocument();
    });
    
    // Simulate browser forward
    window.history.forward();
    
    await waitFor(() => {
      expect(screen.getByTestId('settings-page')).toBeInTheDocument();
    });
  });

  it('handles nested routes correctly', async () => {
    renderApp('/users/123');
    
    expect(screen.getByTestId('user-detail-page')).toBeInTheDocument();
    expect(screen.getByTestId('nav-users')).toHaveClass('active');
  });

  it('handles route parameters', () => {
    renderApp('/users/456/edit');
    
    const userEditPage = screen.getByTestId('user-edit-page');
    expect(userEditPage).toBeInTheDocument();
    expect(userEditPage).toHaveAttribute('data-user-id', '456');
  });

  it('handles protected routes', () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <AppWithNavigation />
      </MemoryRouter>,
      {
        initialAuthState: {
          isAuthenticated: true,
          user: { ...testUser, role: 'user' }, // Non-admin user
          currentOrganization: testOrganization
        }
      }
    );
    
    expect(screen.getByTestId('unauthorized-page')).toBeInTheDocument();
  });

  it('handles navigation with query parameters', async () => {
    renderApp('/users?page=2&sort=name');
    
    const usersPage = screen.getByTestId('users-page');
    expect(usersPage).toHaveAttribute('data-page', '2');
    expect(usersPage).toHaveAttribute('data-sort', 'name');
  });

  it('preserves navigation state during page changes', async () => {
    renderApp('/');
    
    // Expand a collapsible nav section
    await user.click(screen.getByTestId('nav-section-toggle'));
    
    await waitFor(() => {
      expect(screen.getByTestId('nav-section-content')).toBeVisible();
    });
    
    // Navigate to another page
    await user.click(screen.getByTestId('nav-users'));
    
    // Nav section should remain expanded
    expect(screen.getByTestId('nav-section-content')).toBeVisible();
  });
});
```

---

## Best Practices for Integration Testing

1. **Test user workflows** - Focus on complete user journeys rather than isolated functionality
2. **Use realistic data** - Use data that represents actual usage patterns
3. **Mock external services** - Use MSW or similar tools for consistent API mocking
4. **Test error scenarios** - Include network errors, API failures, and edge cases
5. **Test concurrent operations** - Ensure the app handles multiple simultaneous actions
6. **Test navigation flows** - Verify routing, URL changes, and browser navigation
7. **Test authentication flows** - Include login, logout, and token refresh scenarios
8. **Test data consistency** - Verify data flows correctly between components
9. **Test performance** - Ensure integration doesn't cause performance issues
10. **Test accessibility** - Verify keyboard navigation and screen reader compatibility

---

**Last Updated**: February 2026
