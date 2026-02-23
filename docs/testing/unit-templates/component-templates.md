# Component Test Templates

Templates for testing React components in the XFD (CyHy Dashboard) frontend application.

> **📝 Important Note**: The XFD codebase currently has mixed import patterns for test-utils. These templates use the recommended pattern (`import { render, screen } from 'test-utils'`), but you may see existing tests using `'test-utils/test-utils'`, `'@/test-utils/test-utils'`, or direct `@testing-library/react` imports. For new tests, use the patterns shown in these templates.

## Table of Contentsponent Test Templates

Templates for testing React components in the XFD frontend application.

## Table of Contents

- [Basic Component Template](#basic-component-template)
- [Component with Props Template](#component-with-props-template)
- [Component with Authentication Template](#component-with-authentication-template)
- [Material-UI Component Template](#material-ui-component-template)
- [Form Component Template](#form-component-template)
- [Component with API Integration Template](#component-with-api-integration-template)
- [Modal/Dialog Component Template](#modaldialog-component-template)

---

## Basic Component Template

Use this for simple components without complex props or state.

```tsx
import React from 'react';
import { render, screen } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { YourComponent } from '../../../components/Path/YourComponent';

// Mock external dependencies if needed
vi.mock('external-library', () => ({
  someFunction: vi.fn()
}));

describe('YourComponent', () => {
  it('renders without crashing', () => {
    render(<YourComponent />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('displays the correct content', () => {
    render(<YourComponent />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });

  it('matches snapshot', () => {
    const { asFragment } = render(<YourComponent />);
    expect(asFragment()).toMatchSnapshot();
  });
});
```

> **💡 Import Pattern Note**: This example uses `import { render, screen } from 'test-utils'` which includes the custom render function with pre-configured providers. Some existing tests use `import { render, screen } from '@testing-library/react'` directly, which may cause issues if your component needs AuthContext, Router, or Theme providers.

---

## Component with Props Template

Use this for components that accept props and need to test different prop combinations.

```tsx
import React from 'react';
import { render, screen } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { YourComponent } from '../../../components/Path/YourComponent';

// Define prop types for better testing
interface YourComponentProps {
  title: string;
  isVisible?: boolean;
  onAction?: () => void;
  data?: any[];
}

const defaultProps: YourComponentProps = {
  title: 'Test Title',
  isVisible: true,
  onAction: vi.fn(),
  data: []
};

describe('YourComponent', () => {
  it('renders with default props', () => {
    render(<YourComponent {...defaultProps} />);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('handles optional props correctly', () => {
    const { rerender } = render(<YourComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();

    // Test with different props
    rerender(<YourComponent title="Updated" isVisible={false} />);
    expect(screen.getByText('Updated')).toBeInTheDocument();
  });

  it('calls prop functions when expected', async () => {
    const mockAction = vi.fn();
    render(<YourComponent {...defaultProps} onAction={mockAction} />);
    
    const button = screen.getByRole('button', { name: /action/i });
    await user.click(button);
    
    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it('renders correctly with data prop', () => {
    const testData = [{ id: 1, name: 'Item 1' }, { id: 2, name: 'Item 2' }];
    render(<YourComponent {...defaultProps} data={testData} />);
    
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
    render(<YourComponent {...defaultProps} data={[]} />);
    expect(screen.getByText(/no items/i)).toBeInTheDocument();
  });
});
```

---

## Component with Authentication Template

Use this for components that depend on authentication context.

```tsx
import React from 'react';
import { render, screen } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { testUser, testOrganization } from 'test-utils';
import { YourComponent } from '../../../components/Path/YourComponent';

describe('YourComponent Authentication', () => {
  it('renders for authenticated user', () => {
    render(<YourComponent />, {
      authContext: {
        user: testUser,
        isAuthenticated: true,
        currentOrganization: testOrganization
      }
    });
    
    expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    expect(screen.getByText(testUser.fullName)).toBeInTheDocument();
  });

  it('shows limited content for unauthenticated user', () => {
    render(<YourComponent />, {
      authContext: {
        user: null,
        isAuthenticated: false,
        currentOrganization: null
      }
    });
    
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
    expect(screen.queryByText(/welcome/i)).not.toBeInTheDocument();
  });

  it('handles different user types correctly', () => {
    const adminUser = { ...testUser, user_type: 'globalAdmin' };
    
    render(<YourComponent />, {
      authContext: {
        user: adminUser,
        isAuthenticated: true,
        currentOrganization: testOrganization
      }
    });
    
    expect(screen.getByText(/admin panel/i)).toBeInTheDocument();
  });

  it('shows organization-specific content', () => {
    render(<YourComponent />, {
      authContext: {
        user: testUser,
        isAuthenticated: true,
        currentOrganization: testOrganization
      }
    });
    
    expect(screen.getByText(testOrganization.name)).toBeInTheDocument();
  });
});
```

---

## Material-UI Component Template

Use this for components that heavily use Material-UI components.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { YourMUIComponent } from '../../../components/Path/YourMUIComponent';

describe('YourMUIComponent', () => {
  it('renders MUI DataGrid correctly', () => {
    const testData = [
      { id: 1, name: 'Item 1', status: 'active' },
      { id: 2, name: 'Item 2', status: 'inactive' }
    ];
    
    render(<YourMUIComponent data={testData} />);
    
    // Test grid presence
    expect(screen.getByRole('grid')).toBeInTheDocument();
    
    // Test grid cells
    const cells = screen.getAllByRole('gridcell');
    expect(cells).toHaveLength(6); // 2 rows × 3 columns
    
    // Test specific content
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
  });

  it('handles MUI dialog interactions', async () => {
    const mockClose = vi.fn();
    render(<YourMUIComponent open={true} onClose={mockClose} />);
    
    // Dialog should be visible
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    
    // Test close functionality
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    
    expect(mockClose).toHaveBeenCalledTimes(1);
  });

  it('tests MUI form validation', async () => {
    render(<YourMUIComponent />);
    
    const submitButton = screen.getByRole('button', { name: /submit/i });
    const textField = screen.getByLabelText(/required field/i);
    
    // Try to submit without filling required field
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/field is required/i)).toBeInTheDocument();
    });
    
    // Fill field and submit
    fireEvent.change(textField, { target: { value: 'test value' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.queryByText(/field is required/i)).not.toBeInTheDocument();
    });
  });

  it('handles MUI loading states', async () => {
    render(<YourMUIComponent loading={true} />);
    
    // Check for MUI CircularProgress or Skeleton
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    
    // Test loaded state
    const { rerender } = render(<YourMUIComponent loading={true} />);
    rerender(<YourMUIComponent loading={false} data={[]} />);
    
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });
});
```

---

## Form Component Template

Use this for form components with validation and submission.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { YourFormComponent } from '../../../components/Path/YourFormComponent';

const mockSubmit = vi.fn();

describe('YourFormComponent', () => {
  beforeEach(() => {
    mockSubmit.mockClear();
  });

  it('renders all form fields', () => {
    render(<YourFormComponent onSubmit={mockSubmit} />);
    
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    render(<YourFormComponent onSubmit={mockSubmit} />);
    
    const submitButton = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
    
    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('validates email format', async () => {
    render(<YourFormComponent onSubmit={mockSubmit} />);
    
    const emailField = screen.getByLabelText(/email/i);
    fireEvent.change(emailField, { target: { value: 'invalid-email' } });
    fireEvent.blur(emailField);
    
    await waitFor(() => {
      expect(screen.getByText(/invalid email format/i)).toBeInTheDocument();
    });
  });

  it('submits form with valid data', async () => {
    render(<YourFormComponent onSubmit={mockSubmit} />);
    
    // Fill out form
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: 'John Doe' }
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'john@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: 'Test message' }
    });
    
    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    
    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith({
        name: 'John Doe',
        email: 'john@example.com',
        message: 'Test message'
      });
    });
  });

  it('shows loading state during submission', async () => {
    render(<YourFormComponent onSubmit={mockSubmit} isLoading={true} />);
    
    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).toBeDisabled();
    expect(screen.getByText(/submitting/i)).toBeInTheDocument();
  });

  it('handles submission errors', async () => {
    const mockError = vi.fn().mockRejectedValue(new Error('Submission failed'));
    render(<YourFormComponent onSubmit={mockError} />);
    
    // Fill and submit form
    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: 'John Doe' }
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'john@example.com' }
    });
    
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/submission failed/i)).toBeInTheDocument();
    });
  });
});
```

---

## Component with API Integration Template

Use this for components that make API calls or integrate with backend services.

```tsx
import React from 'react';
import { render, screen, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { YourAPIComponent } from '../../../components/Path/YourAPIComponent';

// Mock the API module
vi.mock('../../../api/endpoints', () => ({
  fetchData: vi.fn(),
  postData: vi.fn(),
  updateData: vi.fn(),
  deleteData: vi.fn()
}));

import { fetchData, postData } from '../../../api/endpoints';
const mockFetchData = vi.mocked(fetchData);
const mockPostData = vi.mocked(postData);

describe('YourAPIComponent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and displays data from API', async () => {
    const mockData = [
      { id: 1, name: 'Item 1' },
      { id: 2, name: 'Item 2' }
    ];
    
    mockFetchData.mockResolvedValue({ data: mockData, status: 200 });
    
    render(<YourAPIComponent />);
    
    // Initially shows loading
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
      expect(screen.getByText('Item 2')).toBeInTheDocument();
    });
    
    expect(mockFetchData).toHaveBeenCalledTimes(1);
  });

  it('handles API loading states', async () => {
    mockFetchData.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ data: [] }), 100))
    );
    
    render(<YourAPIComponent />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    expect(screen.queryByText(/no items/i)).not.toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
      expect(screen.getByText(/no items/i)).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockFetchData.mockRejectedValue(new Error('API Error'));
    
    render(<YourAPIComponent />);
    
    await waitFor(() => {
      expect(screen.getByText(/error loading data/i)).toBeInTheDocument();
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
    
    consoleError.mockRestore();
  });

  it('handles data submission', async () => {
    mockPostData.mockResolvedValue({ data: { id: 3, name: 'New Item' }, status: 201 });
    
    render(<YourAPIComponent />);
    
    // Fill form and submit
    const input = screen.getByLabelText(/name/i);
    const submitButton = screen.getByRole('button', { name: /add/i });
    
    fireEvent.change(input, { target: { value: 'New Item' } });
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(mockPostData).toHaveBeenCalledWith({ name: 'New Item' });
      expect(screen.getByText('New Item')).toBeInTheDocument();
    });
  });

  it('retries failed requests', async () => {
    mockFetchData
      .mockRejectedValueOnce(new Error('Network Error'))
      .mockResolvedValue({ data: [{ id: 1, name: 'Item 1' }] });
    
    render(<YourAPIComponent />);
    
    // Click retry button
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    
    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
      expect(mockFetchData).toHaveBeenCalledTimes(2);
    });
  });
});
```

---

## Modal/Dialog Component Template

Use this for modal and dialog components.

```tsx
import React from 'react';
import { render, screen, fireEvent } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { YourModalComponent } from '../../../components/Path/YourModalComponent';

describe('YourModalComponent', () => {
  const mockOnClose = vi.fn();
  const mockOnConfirm = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when open', () => {
    render(
      <YourModalComponent 
        open={true} 
        onClose={mockOnClose} 
        onConfirm={mockOnConfirm}
      />
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/modal title/i)).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <YourModalComponent 
        open={false} 
        onClose={mockOnClose} 
        onConfirm={mockOnConfirm}
      />
    );
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    render(
      <YourModalComponent 
        open={true} 
        onClose={mockOnClose} 
        onConfirm={mockOnConfirm}
      />
    );
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('calls onConfirm when confirm button clicked', () => {
    render(
      <YourModalComponent 
        open={true} 
        onClose={mockOnClose} 
        onConfirm={mockOnConfirm}
      />
    );
    
    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    fireEvent.click(confirmButton);
    
    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('handles keyboard interactions', () => {
    render(
      <YourModalComponent 
        open={true} 
        onClose={mockOnClose} 
        onConfirm={mockOnConfirm}
      />
    );
    
    // Test Escape key
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('traps focus within modal', () => {
    render(
      <YourModalComponent 
        open={true} 
        onClose={mockOnClose} 
        onConfirm={mockOnConfirm}
      />
    );
    
    const modal = screen.getByRole('dialog');
    const firstFocusableElement = screen.getByRole('button', { name: /close/i });
    const lastFocusableElement = screen.getByRole('button', { name: /confirm/i });
    
    // Focus should start on first focusable element
    expect(document.activeElement).toBe(firstFocusableElement);
    
    // Tab to last element
    fireEvent.keyDown(modal, { key: 'Tab', shiftKey: false });
    expect(document.activeElement).toBe(lastFocusableElement);
    
    // Shift+Tab back to first element
    fireEvent.keyDown(modal, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(firstFocusableElement);
  });
});
```

---

## Best Practices

1. **Always test the happy path first** - ensure basic functionality works
2. **Test edge cases and error states** - empty data, network failures, validation errors
3. **Use semantic queries** - `getByRole`, `getByLabelText`, `getByText` instead of `getByTestId`
4. **Mock external dependencies** - APIs, third-party libraries, complex child components
5. **Test user interactions** - clicks, form submissions, keyboard navigation
6. **Keep tests focused** - one concept per test, clear test names
7. **Use the custom render function** - ensures consistent provider setup
8. **Clean up after tests** - reset mocks, clear timers, clean up side effects

---

**Last Updated**: February 2026
