# Component Test Templates

General patterns for testing React components in the XFD frontend application.

> **💡 Key Principle**: Use the custom `render` function from `test-utils` which automatically provides all necessary providers (AuthContext, Router, Theme). This eliminates ad-hoc render setups and ensures consistency.

## Basic Component Template

```tsx
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { YourComponent } from '@/components/Path/YourComponent';

describe('YourComponent', () => {
  it('renders without crashing', () => {
    render(<YourComponent />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('displays expected content', () => {
    render(<YourComponent />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });

  it('handles user interactions', async () => {
    const mockHandler = vi.fn();
    render(<YourComponent onAction={mockHandler} />);
    
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    await waitFor(() => expect(mockHandler).toHaveBeenCalled());
  });
});
```

## Component with Authentication

```tsx
import { render, screen } from 'test-utils';
import { testUser, testOrganization } from 'test-utils';
import { describe, expect, it } from 'vitest';
import { YourComponent } from '@/components/Path/YourComponent';

describe('YourComponent with authentication', () => {
  it('renders for authenticated user', () => {
    render(<YourComponent />, { 
      authContext: { 
        user: testUser, 
        isAuthenticated: true,
        currentOrganization: testOrganization 
      } 
    });
    
    expect(screen.getByText('Welcome')).toBeInTheDocument();
  });

  it('renders for unauthenticated user', () => {
    render(<YourComponent />, { 
      authContext: { 
        user: null, 
        isAuthenticated: false 
      } 
    });
    
    expect(screen.getByText('Please log in')).toBeInTheDocument();
  });
});
```

## Component with API Calls

```tsx
import { render, screen, waitFor } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { useApi } from '@/hooks/useApi';
import { YourComponent } from '@/components/Path/YourComponent';

// Mock API modules
vi.mock('@/hooks/useApi');

describe('YourComponent with API', () => {
  it('displays loading state', () => {
    const mockUseApi = vi.mocked(useApi);
    mockUseApi.mockReturnValue({ 
      data: null, 
      loading: true, 
      error: null 
    });

    render(<YourComponent />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('displays data when loaded', async () => {
    const mockData = { name: 'Test Data' };
    const mockUseApi = vi.mocked(useApi);
    mockUseApi.mockReturnValue({ 
      data: mockData, 
      loading: false, 
      error: null 
    });

    render(<YourComponent />);
    await waitFor(() => {
      expect(screen.getByText('Test Data')).toBeInTheDocument();
    });
  });

  it('displays error state', () => {
    const mockUseApi = vi.mocked(useApi);
    mockUseApi.mockReturnValue({ 
      data: null, 
      loading: false, 
      error: new Error('API Error') 
    });

    render(<YourComponent />);
    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });
});
```

## Key Patterns

### Centralized Testing Approach
- **Always use custom `render` from `test-utils`** - automatically includes all providers
- **Import mock data from `test-utils`** - (`testUser`, `testOrganization`, etc.)
- **Use `@` aliases for component imports** - consistent import patterns

### The Custom Render Function
When you import `render` from `test-utils`, you get a pre-configured function that includes:
- AuthContext with default values (from `authCtx`)
- Router (MemoryRouter) for navigation
- Theme providers (CFThemeProvider)
- Navigation context

**Override defaults when needed:**
```tsx
// Default usage - uses all default providers
render(<YourComponent />);

// Override auth context for specific test scenarios
render(<YourComponent />, { 
  authContext: { user: testUser, isAuthenticated: true } 
});
```

### Focus on Testing Logic, Not Setup
The centralized approach means you can focus on testing component behavior rather than provider setup:

- **Test what the component does** - user interactions, state changes, conditional rendering
- **Test different scenarios** - authenticated vs unauthenticated, loading vs loaded states  
- **Mock external dependencies** - APIs, hooks, utilities
- **Use semantic queries** - `getByRole`, `getByLabelText`, `getByText`

### Common Anti-Patterns to Avoid
- ❌ Manual provider wrapping - `<AuthContext.Provider><YourComponent /></AuthContext.Provider>`
- ❌ Importing from `@testing-library/react` directly when you need providers
- ❌ Duplicating provider setup across test files

---

**Last Updated**: March 2026
