# Context Test Templates

Templates for testing React Context providers in the XFD frontend application.

> **📝 Important Note**: The XFD codebase currently has mixed import patterns for test-utils. These templates use the recommended pattern (`import { render, screen } from 'test-utils'`), but you may see existing tests using different patterns. For new tests, use the patterns shown in these templates.

## Table of Contents

- [Basic Context Provider Template](#basic-context-provider-template)
- [Context with State Management Template](#context-with-state-management-template)
- [Context with API Integration Template](#context-with-api-integration-template)
- [Context with Authentication Template](#context-with-authentication-template)
- [Context Hook Testing Template](#context-hook-testing-template)
- [Nested Context Providers Template](#nested-context-providers-template)

---

## Basic Context Provider Template

Use this for simple context providers that share data or state.

```tsx
import React from 'react';
import { render, screen, fireEvent } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { YourContextProvider, YourContext, useYourContext } from '../../context/YourContext';

// Test component that uses the context
const TestConsumer: React.FC = () => {
  const contextValue = useYourContext();
  
  return (
    <div>
      <div data-testid="context-value">{JSON.stringify(contextValue)}</div>
      <button 
        onClick={() => contextValue.updateValue('new-value')}
        data-testid="update-button"
      >
        Update
      </button>
    </div>
  );
};

describe('YourContextProvider', () => {
  it('provides initial context value', () => {
    render(
      <YourContextProvider>
        <TestConsumer />
      </YourContextProvider>
    );
    
    const contextDisplay = screen.getByTestId('context-value');
    const contextValue = JSON.parse(contextDisplay.textContent || '{}');
    
    expect(contextValue).toMatchObject({
      value: 'initialValue',
      updateValue: expect.any(Function)
    });
  });

  it('updates context value correctly', () => {
    render(
      <YourContextProvider>
        <TestConsumer />
      </YourContextProvider>
    );
    
    const updateButton = screen.getByTestId('update-button');
    fireEvent.click(updateButton);
    
    const contextDisplay = screen.getByTestId('context-value');
    const contextValue = JSON.parse(contextDisplay.textContent || '{}');
    
    expect(contextValue.value).toBe('new-value');
  });

  it('provides stable function references', () => {
    let firstUpdateFunction: any;
    let secondUpdateFunction: any;
    
    const TestStability: React.FC = () => {
      const { updateValue } = useYourContext();
      
      if (!firstUpdateFunction) {
        firstUpdateFunction = updateValue;
      } else {
        secondUpdateFunction = updateValue;
      }
      
      return <div data-testid="stability-test">Tested</div>;
    };
    
    const { rerender } = render(
      <YourContextProvider>
        <TestStability />
      </YourContextProvider>
    );
    
    rerender(
      <YourContextProvider>
        <TestStability />
      </YourContextProvider>
    );
    
    expect(firstUpdateFunction).toBe(secondUpdateFunction);
  });

  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    const TestOutsideProvider: React.FC = () => {
      useYourContext(); // This should throw
      return <div>Should not render</div>;
    };
    
    expect(() => {
      render(<TestOutsideProvider />);
    }).toThrow('useYourContext must be used within YourContextProvider');
    
    consoleError.mockRestore();
  });

  it('handles multiple consumers correctly', () => {
    const Consumer1: React.FC = () => {
      const { value } = useYourContext();
      return <div data-testid="consumer-1">{value}</div>;
    };
    
    const Consumer2: React.FC = () => {
      const { value } = useYourContext();
      return <div data-testid="consumer-2">{value}</div>;
    };
    
    render(
      <YourContextProvider>
        <Consumer1 />
        <Consumer2 />
      </YourContextProvider>
    );
    
    expect(screen.getByTestId('consumer-1')).toHaveTextContent('initialValue');
    expect(screen.getByTestId('consumer-2')).toHaveTextContent('initialValue');
  });
});
```

---

## Context with State Management Template

Use this for contexts that manage complex state with reducers or multiple state values.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { 
  StateContextProvider, 
  useStateContext, 
  StateAction 
} from '../../context/StateContext';

// Mock initial state
const mockInitialState = {
  data: [],
  isLoading: false,
  error: null,
  filters: {},
  pagination: { page: 1, pageSize: 10 }
};

const TestStateConsumer: React.FC = () => {
  const { state, dispatch } = useStateContext();
  
  const handleAddItem = () => {
    dispatch({
      type: 'ADD_ITEM',
      payload: { id: Date.now(), name: 'New Item' }
    });
  };
  
  const handleSetLoading = () => {
    dispatch({ type: 'SET_LOADING', payload: true });
  };
  
  const handleSetError = () => {
    dispatch({ 
      type: 'SET_ERROR', 
      payload: new Error('Test error') 
    });
  };
  
  return (
    <div>
      <div data-testid="state-data">{JSON.stringify(state)}</div>
      <button onClick={handleAddItem} data-testid="add-item">
        Add Item
      </button>
      <button onClick={handleSetLoading} data-testid="set-loading">
        Set Loading
      </button>
      <button onClick={handleSetError} data-testid="set-error">
        Set Error
      </button>
    </div>
  );
};

describe('StateContextProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('provides initial state correctly', () => {
    render(
      <StateContextProvider>
        <TestStateConsumer />
      </StateContextProvider>
    );
    
    const stateDisplay = screen.getByTestId('state-data');
    const state = JSON.parse(stateDisplay.textContent || '{}');
    
    expect(state).toMatchObject(mockInitialState);
  });

  it('handles ADD_ITEM action correctly', () => {
    render(
      <StateContextProvider>
        <TestStateConsumer />
      </StateContextProvider>
    );
    
    const addButton = screen.getByTestId('add-item');
    fireEvent.click(addButton);
    
    const stateDisplay = screen.getByTestId('state-data');
    const state = JSON.parse(stateDisplay.textContent || '{}');
    
    expect(state.data).toHaveLength(1);
    expect(state.data[0]).toMatchObject({
      id: expect.any(Number),
      name: 'New Item'
    });
  });

  it('handles SET_LOADING action correctly', () => {
    render(
      <StateContextProvider>
        <TestStateConsumer />
      </StateContextProvider>
    );
    
    const loadingButton = screen.getByTestId('set-loading');
    fireEvent.click(loadingButton);
    
    const stateDisplay = screen.getByTestId('state-data');
    const state = JSON.parse(stateDisplay.textContent || '{}');
    
    expect(state.isLoading).toBe(true);
  });

  it('handles SET_ERROR action correctly', () => {
    render(
      <StateContextProvider>
        <TestStateConsumer />
      </StateContextProvider>
    );
    
    const errorButton = screen.getByTestId('set-error');
    fireEvent.click(errorButton);
    
    const stateDisplay = screen.getByTestId('state-data');
    const state = JSON.parse(stateDisplay.textContent || '{}');
    
    expect(state.error).toBeTruthy();
    expect(state.error.message).toBe('Test error');
  });

  it('handles multiple actions in sequence', () => {
    render(
      <StateContextProvider>
        <TestStateConsumer />
      </StateContextProvider>
    );
    
    // Add multiple items
    const addButton = screen.getByTestId('add-item');
    fireEvent.click(addButton);
    fireEvent.click(addButton);
    fireEvent.click(addButton);
    
    const stateDisplay = screen.getByTestId('state-data');
    const state = JSON.parse(stateDisplay.textContent || '{}');
    
    expect(state.data).toHaveLength(3);
    expect(state.data.every(item => item.name === 'New Item')).toBe(true);
  });

  it('maintains state consistency across re-renders', () => {
    const { rerender } = render(
      <StateContextProvider>
        <TestStateConsumer />
      </StateContextProvider>
    );
    
    // Add an item
    const addButton = screen.getByTestId('add-item');
    fireEvent.click(addButton);
    
    // Force re-render
    rerender(
      <StateContextProvider>
        <TestStateConsumer />
      </StateContextProvider>
    );
    
    const stateDisplay = screen.getByTestId('state-data');
    const state = JSON.parse(stateDisplay.textContent || '{}');
    
    expect(state.data).toHaveLength(1);
  });

  it('provides stable dispatch function', () => {
    let firstDispatch: any;
    let secondDispatch: any;
    
    const TestDispatchStability: React.FC = () => {
      const { dispatch } = useStateContext();
      
      if (!firstDispatch) {
        firstDispatch = dispatch;
      } else {
        secondDispatch = dispatch;
      }
      
      return <div data-testid="dispatch-stability">Tested</div>;
    };
    
    const { rerender } = render(
      <StateContextProvider>
        <TestDispatchStability />
      </StateContextProvider>
    );
    
    rerender(
      <StateContextProvider>
        <TestDispatchStability />
      </StateContextProvider>
    );
    
    expect(firstDispatch).toBe(secondDispatch);
  });
});
```

---

## Context with API Integration Template

Use this for contexts that handle API calls and data fetching.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { APIContextProvider, useAPIContext } from '../../context/APIContext';

// Mock API
vi.mock('../../api/endpoints', () => ({
  fetchData: vi.fn(),
  postData: vi.fn(),
  updateData: vi.fn(),
  deleteData: vi.fn()
}));

import { fetchData, postData, updateData, deleteData } from '../../api/endpoints';
const mockFetchData = vi.mocked(fetchData);
const mockPostData = vi.mocked(postData);
const mockUpdateData = vi.mocked(updateData);
const mockDeleteData = vi.mocked(deleteData);

const TestAPIConsumer: React.FC = () => {
  const { 
    data, 
    isLoading, 
    error, 
    fetchItems, 
    createItem, 
    updateItem, 
    deleteItem,
    clearError 
  } = useAPIContext();
  
  return (
    <div>
      <div data-testid="api-data">{JSON.stringify({ data, isLoading, error: error?.message })}</div>
      <button onClick={() => fetchItems()} data-testid="fetch-items">
        Fetch Items
      </button>
      <button onClick={() => createItem({ name: 'New Item' })} data-testid="create-item">
        Create Item
      </button>
      <button onClick={() => updateItem(1, { name: 'Updated Item' })} data-testid="update-item">
        Update Item
      </button>
      <button onClick={() => deleteItem(1)} data-testid="delete-item">
        Delete Item
      </button>
      <button onClick={clearError} data-testid="clear-error">
        Clear Error
      </button>
    </div>
  );
};

describe('APIContextProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('provides initial API state', () => {
    render(
      <APIContextProvider>
        <TestAPIConsumer />
      </APIContextProvider>
    );
    
    const apiDisplay = screen.getByTestId('api-data');
    const apiState = JSON.parse(apiDisplay.textContent || '{}');
    
    expect(apiState).toMatchObject({
      data: null,
      isLoading: false,
      error: null
    });
  });

  it('handles successful data fetching', async () => {
    const mockData = [{ id: 1, name: 'Item 1' }, { id: 2, name: 'Item 2' }];
    mockFetchData.mockResolvedValue({ data: mockData, status: 200 });
    
    render(
      <APIContextProvider>
        <TestAPIConsumer />
      </APIContextProvider>
    );
    
    const fetchButton = screen.getByTestId('fetch-items');
    fireEvent.click(fetchButton);
    
    // Should show loading initially
    await waitFor(() => {
      const apiDisplay = screen.getByTestId('api-data');
      const apiState = JSON.parse(apiDisplay.textContent || '{}');
      expect(apiState.isLoading).toBe(true);
    });
    
    // Should show data when loaded
    await waitFor(() => {
      const apiDisplay = screen.getByTestId('api-data');
      const apiState = JSON.parse(apiDisplay.textContent || '{}');
      expect(apiState.isLoading).toBe(false);
      expect(apiState.data).toEqual(mockData);
    });
    
    expect(mockFetchData).toHaveBeenCalledTimes(1);
  });

  it('handles API errors correctly', async () => {
    const error = new Error('API Error');
    mockFetchData.mockRejectedValue(error);
    
    render(
      <APIContextProvider>
        <TestAPIConsumer />
      </APIContextProvider>
    );
    
    const fetchButton = screen.getByTestId('fetch-items');
    fireEvent.click(fetchButton);
    
    await waitFor(() => {
      const apiDisplay = screen.getByTestId('api-data');
      const apiState = JSON.parse(apiDisplay.textContent || '{}');
      expect(apiState.isLoading).toBe(false);
      expect(apiState.error).toBe('API Error');
    });
  });

  it('handles item creation', async () => {
    const newItem = { id: 3, name: 'New Item' };
    mockPostData.mockResolvedValue({ data: newItem, status: 201 });
    
    render(
      <APIContextProvider>
        <TestAPIConsumer />
      </APIContextProvider>
    );
    
    const createButton = screen.getByTestId('create-item');
    fireEvent.click(createButton);
    
    await waitFor(() => {
      expect(mockPostData).toHaveBeenCalledWith({ name: 'New Item' });
    });
  });

  it('handles item updates', async () => {
    const updatedItem = { id: 1, name: 'Updated Item' };
    mockUpdateData.mockResolvedValue({ data: updatedItem, status: 200 });
    
    render(
      <APIContextProvider>
        <TestAPIConsumer />
      </APIContextProvider>
    );
    
    const updateButton = screen.getByTestId('update-item');
    fireEvent.click(updateButton);
    
    await waitFor(() => {
      expect(mockUpdateData).toHaveBeenCalledWith(1, { name: 'Updated Item' });
    });
  });

  it('handles item deletion', async () => {
    mockDeleteData.mockResolvedValue({ status: 204 });
    
    render(
      <APIContextProvider>
        <TestAPIConsumer />
      </APIContextProvider>
    );
    
    const deleteButton = screen.getByTestId('delete-item');
    fireEvent.click(deleteButton);
    
    await waitFor(() => {
      expect(mockDeleteData).toHaveBeenCalledWith(1);
    });
  });

  it('clears errors correctly', async () => {
    const error = new Error('Test Error');
    mockFetchData.mockRejectedValue(error);
    
    render(
      <APIContextProvider>
        <TestAPIConsumer />
      </APIContextProvider>
    );
    
    // Trigger error
    const fetchButton = screen.getByTestId('fetch-items');
    fireEvent.click(fetchButton);
    
    await waitFor(() => {
      const apiDisplay = screen.getByTestId('api-data');
      const apiState = JSON.parse(apiDisplay.textContent || '{}');
      expect(apiState.error).toBe('Test Error');
    });
    
    // Clear error
    const clearButton = screen.getByTestId('clear-error');
    fireEvent.click(clearButton);
    
    const apiDisplay = screen.getByTestId('api-data');
    const apiState = JSON.parse(apiDisplay.textContent || '{}');
    expect(apiState.error).toBe(null);
  });

  it('handles concurrent API calls correctly', async () => {
    let resolveFirst: (value: any) => void;
    let resolveSecond: (value: any) => void;
    
    const firstPromise = new Promise(resolve => { resolveFirst = resolve; });
    const secondPromise = new Promise(resolve => { resolveSecond = resolve; });
    
    mockFetchData
      .mockReturnValueOnce(firstPromise)
      .mockReturnValueOnce(secondPromise);
    
    render(
      <APIContextProvider>
        <TestAPIConsumer />
      </APIContextProvider>
    );
    
    const fetchButton = screen.getByTestId('fetch-items');
    
    // Start first request
    fireEvent.click(fetchButton);
    
    // Start second request before first completes
    fireEvent.click(fetchButton);
    
    // Resolve second request first
    resolveSecond!({ data: ['second'], status: 200 });
    
    await waitFor(() => {
      const apiDisplay = screen.getByTestId('api-data');
      const apiState = JSON.parse(apiDisplay.textContent || '{}');
      expect(apiState.data).toEqual(['second']);
    });
    
    // Resolve first request (should be ignored due to cancellation)
    resolveFirst!({ data: ['first'], status: 200 });
    
    // Should still show second request result
    await waitFor(() => {
      const apiDisplay = screen.getByTestId('api-data');
      const apiState = JSON.parse(apiDisplay.textContent || '{}');
      expect(apiState.data).toEqual(['second']);
    });
  });
});
```

---

## Context with Authentication Template

Use this for authentication contexts that manage user state and authentication flow.

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { testUser, testOrganization } from 'test-utils';
import { AuthContextProvider, useAuthContext } from '../../context/AuthContext';

// Mock authentication service
vi.mock('../../services/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  getCurrentUser: vi.fn(),
  refreshToken: vi.fn()
}));

import { login, logout, getCurrentUser, refreshToken } from '../../services/auth';
const mockLogin = vi.mocked(login);
const mockLogout = vi.mocked(logout);
const mockGetCurrentUser = vi.mocked(getCurrentUser);
const mockRefreshToken = vi.mocked(refreshToken);

const TestAuthConsumer: React.FC = () => {
  const { 
    user, 
    isAuthenticated, 
    isLoading, 
    currentOrganization,
    login: contextLogin,
    logout: contextLogout,
    switchOrganization,
    refreshUser
  } = useAuthContext();
  
  return (
    <div>
      <div data-testid="auth-state">
        {JSON.stringify({ 
          user: user?.name, 
          isAuthenticated, 
          isLoading,
          currentOrganization: currentOrganization?.name
        })}
      </div>
      <button 
        onClick={() => contextLogin('test@example.com', 'password')}
        data-testid="login-button"
      >
        Login
      </button>
      <button onClick={contextLogout} data-testid="logout-button">
        Logout
      </button>
      <button 
        onClick={() => switchOrganization(testOrganization)}
        data-testid="switch-org-button"
      >
        Switch Organization
      </button>
      <button onClick={refreshUser} data-testid="refresh-user-button">
        Refresh User
      </button>
    </div>
  );
};

describe('AuthContextProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
  });

  it('provides initial unauthenticated state', () => {
    render(
      <AuthContextProvider>
        <TestAuthConsumer />
      </AuthContextProvider>
    );
    
    const authDisplay = screen.getByTestId('auth-state');
    const authState = JSON.parse(authDisplay.textContent || '{}');
    
    expect(authState).toMatchObject({
      user: undefined,
      isAuthenticated: false,
      isLoading: false,
      currentOrganization: undefined
    });
  });

  it('handles successful login', async () => {
    const loginResponse = {
      user: testUser,
      token: 'mock-token',
      refreshToken: 'mock-refresh-token'
    };
    mockLogin.mockResolvedValue(loginResponse);
    
    render(
      <AuthContextProvider>
        <TestAuthConsumer />
      </AuthContextProvider>
    );
    
    const loginButton = screen.getByTestId('login-button');
    fireEvent.click(loginButton);
    
    // Should show loading during login
    await waitFor(() => {
      const authDisplay = screen.getByTestId('auth-state');
      const authState = JSON.parse(authDisplay.textContent || '{}');
      expect(authState.isLoading).toBe(true);
    });
    
    // Should show authenticated state after login
    await waitFor(() => {
      const authDisplay = screen.getByTestId('auth-state');
      const authState = JSON.parse(authDisplay.textContent || '{}');
      expect(authState.isLoading).toBe(false);
      expect(authState.isAuthenticated).toBe(true);
      expect(authState.user).toBe(testUser.name);
    });
    
    expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password');
  });

  it('handles login failure', async () => {
    const loginError = new Error('Invalid credentials');
    mockLogin.mockRejectedValue(loginError);
    
    render(
      <AuthContextProvider>
        <TestAuthConsumer />
      </AuthContextProvider>
    );
    
    const loginButton = screen.getByTestId('login-button');
    fireEvent.click(loginButton);
    
    await waitFor(() => {
      const authDisplay = screen.getByTestId('auth-state');
      const authState = JSON.parse(authDisplay.textContent || '{}');
      expect(authState.isLoading).toBe(false);
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.user).toBe(undefined);
    });
  });

  it('handles logout correctly', async () => {
    mockLogout.mockResolvedValue(undefined);
    
    // Start with authenticated state
    render(
      <AuthContextProvider initialUser={testUser}>
        <TestAuthConsumer />
      </AuthContextProvider>
    );
    
    const logoutButton = screen.getByTestId('logout-button');
    fireEvent.click(logoutButton);
    
    await waitFor(() => {
      const authDisplay = screen.getByTestId('auth-state');
      const authState = JSON.parse(authDisplay.textContent || '{}');
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.user).toBe(undefined);
    });
    
    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

  it('handles organization switching', () => {
    render(
      <AuthContextProvider initialUser={testUser}>
        <TestAuthConsumer />
      </AuthContextProvider>
    );
    
    const switchOrgButton = screen.getByTestId('switch-org-button');
    fireEvent.click(switchOrgButton);
    
    const authDisplay = screen.getByTestId('auth-state');
    const authState = JSON.parse(authDisplay.textContent || '{}');
    expect(authState.currentOrganization).toBe(testOrganization.name);
  });

  it('handles user refresh', async () => {
    const updatedUser = { ...testUser, name: 'Updated Name' };
    mockGetCurrentUser.mockResolvedValue(updatedUser);
    
    render(
      <AuthContextProvider initialUser={testUser}>
        <TestAuthConsumer />
      </AuthContextProvider>
    );
    
    const refreshButton = screen.getByTestId('refresh-user-button');
    fireEvent.click(refreshButton);
    
    await waitFor(() => {
      const authDisplay = screen.getByTestId('auth-state');
      const authState = JSON.parse(authDisplay.textContent || '{}');
      expect(authState.user).toBe('Updated Name');
    });
  });

  it('persists authentication state in localStorage', async () => {
    const loginResponse = {
      user: testUser,
      token: 'mock-token',
      refreshToken: 'mock-refresh-token'
    };
    mockLogin.mockResolvedValue(loginResponse);
    
    render(
      <AuthContextProvider>
        <TestAuthConsumer />
      </AuthContextProvider>
    );
    
    const loginButton = screen.getByTestId('login-button');
    fireEvent.click(loginButton);
    
    await waitFor(() => {
      expect(localStorage.getItem('authToken')).toBe('mock-token');
      expect(localStorage.getItem('refreshToken')).toBe('mock-refresh-token');
    });
  });

  it('handles token refresh automatically', async () => {
    const newToken = 'new-mock-token';
    mockRefreshToken.mockResolvedValue({ token: newToken });
    
    render(
      <AuthContextProvider initialUser={testUser}>
        <TestAuthConsumer />
      </AuthContextProvider>
    );
    
    // Simulate token expiration by calling refresh
    await waitFor(() => {
      // Context should handle token refresh internally
      expect(mockRefreshToken).toHaveBeenCalled();
    });
  });

  it('handles multiple consumers correctly', () => {
    const Consumer1: React.FC = () => {
      const { isAuthenticated } = useAuthContext();
      return <div data-testid="consumer-1">{isAuthenticated.toString()}</div>;
    };
    
    const Consumer2: React.FC = () => {
      const { user } = useAuthContext();
      return <div data-testid="consumer-2">{user?.name || 'No user'}</div>;
    };
    
    render(
      <AuthContextProvider initialUser={testUser}>
        <Consumer1 />
        <Consumer2 />
      </AuthContextProvider>
    );
    
    expect(screen.getByTestId('consumer-1')).toHaveTextContent('true');
    expect(screen.getByTestId('consumer-2')).toHaveTextContent(testUser.name);
  });
});
```

---

## Context Hook Testing Template

Use this template specifically for testing custom hooks that consume context.

```tsx
import React from 'react';
import { renderHook, act } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { useYourContextHook } from '../../hooks/useYourContextHook';
import { YourContextProvider } from '../../context/YourContext';

// Mock context value
const mockContextValue = {
  data: 'test-data',
  isLoading: false,
  updateData: vi.fn(),
  resetData: vi.fn()
};

describe('useYourContextHook', () => {
  it('returns context value when used within provider', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={mockContextValue}>
        {children}
      </YourContextProvider>
    );
    
    const { result } = renderHook(() => useYourContextHook(), { wrapper });
    
    expect(result.current).toEqual(mockContextValue);
  });

  it('throws error when used outside provider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      renderHook(() => useYourContextHook());
    }).toThrow('useYourContextHook must be used within YourContextProvider');
    
    consoleError.mockRestore();
  });

  it('provides stable function references', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={mockContextValue}>
        {children}
      </YourContextProvider>
    );
    
    const { result, rerender } = renderHook(() => useYourContextHook(), { wrapper });
    
    const firstUpdateData = result.current.updateData;
    
    rerender();
    
    expect(result.current.updateData).toBe(firstUpdateData);
  });

  it('reflects context value changes', () => {
    let contextValue = { ...mockContextValue, data: 'initial' };
    
    const DynamicProvider = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={contextValue}>
        {children}
      </YourContextProvider>
    );
    
    const { result, rerender } = renderHook(() => useYourContextHook(), {
      wrapper: DynamicProvider
    });
    
    expect(result.current.data).toBe('initial');
    
    // Update context value
    contextValue = { ...contextValue, data: 'updated' };
    rerender();
    
    expect(result.current.data).toBe('updated');
  });

  it('handles context methods correctly', () => {
    const mockUpdate = vi.fn();
    const contextValueWithMock = {
      ...mockContextValue,
      updateData: mockUpdate
    };
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={contextValueWithMock}>
        {children}
      </YourContextProvider>
    );
    
    const { result } = renderHook(() => useYourContextHook(), { wrapper });
    
    act(() => {
      result.current.updateData('new-data');
    });
    
    expect(mockUpdate).toHaveBeenCalledWith('new-data');
  });

  it('handles loading states correctly', () => {
    const loadingContextValue = {
      ...mockContextValue,
      isLoading: true
    };
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <YourContextProvider value={loadingContextValue}>
        {children}
      </YourContextProvider>
    );
    
    const { result } = renderHook(() => useYourContextHook(), { wrapper });
    
    expect(result.current.isLoading).toBe(true);
  });
});
```

---

## Nested Context Providers Template

Use this for testing scenarios with multiple context providers.

```tsx
import React from 'react';
import { render, screen, fireEvent } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { 
  OuterContextProvider,
  InnerContextProvider,
  useOuterContext,
  useInnerContext,
  useCombinedContext
} from '../../context/NestedContexts';

const TestNestedConsumer: React.FC = () => {
  const outerContext = useOuterContext();
  const innerContext = useInnerContext();
  const combinedContext = useCombinedContext();
  
  return (
    <div>
      <div data-testid="outer-value">{outerContext.value}</div>
      <div data-testid="inner-value">{innerContext.value}</div>
      <div data-testid="combined-value">{combinedContext.combinedValue}</div>
      <button 
        onClick={() => outerContext.updateValue('updated-outer')}
        data-testid="update-outer"
      >
        Update Outer
      </button>
      <button 
        onClick={() => innerContext.updateValue('updated-inner')}
        data-testid="update-inner"
      >
        Update Inner
      </button>
    </div>
  );
};

describe('Nested Context Providers', () => {
  it('provides values from both contexts', () => {
    render(
      <OuterContextProvider>
        <InnerContextProvider>
          <TestNestedConsumer />
        </InnerContextProvider>
      </OuterContextProvider>
    );
    
    expect(screen.getByTestId('outer-value')).toHaveTextContent('outer-initial');
    expect(screen.getByTestId('inner-value')).toHaveTextContent('inner-initial');
    expect(screen.getByTestId('combined-value')).toHaveTextContent('outer-initial + inner-initial');
  });

  it('handles outer context updates correctly', () => {
    render(
      <OuterContextProvider>
        <InnerContextProvider>
          <TestNestedConsumer />
        </InnerContextProvider>
      </OuterContextProvider>
    );
    
    const updateButton = screen.getByTestId('update-outer');
    fireEvent.click(updateButton);
    
    expect(screen.getByTestId('outer-value')).toHaveTextContent('updated-outer');
    expect(screen.getByTestId('combined-value')).toHaveTextContent('updated-outer + inner-initial');
  });

  it('handles inner context updates correctly', () => {
    render(
      <OuterContextProvider>
        <InnerContextProvider>
          <TestNestedConsumer />
        </InnerContextProvider>
      </OuterContextProvider>
    );
    
    const updateButton = screen.getByTestId('update-inner');
    fireEvent.click(updateButton);
    
    expect(screen.getByTestId('inner-value')).toHaveTextContent('updated-inner');
    expect(screen.getByTestId('combined-value')).toHaveTextContent('outer-initial + updated-inner');
  });

  it('handles independent context updates', () => {
    render(
      <OuterContextProvider>
        <InnerContextProvider>
          <TestNestedConsumer />
        </InnerContextProvider>
      </OuterContextProvider>
    );
    
    // Update both contexts
    fireEvent.click(screen.getByTestId('update-outer'));
    fireEvent.click(screen.getByTestId('update-inner'));
    
    expect(screen.getByTestId('outer-value')).toHaveTextContent('updated-outer');
    expect(screen.getByTestId('inner-value')).toHaveTextContent('updated-inner');
    expect(screen.getByTestId('combined-value')).toHaveTextContent('updated-outer + updated-inner');
  });

  it('maintains context isolation', () => {
    const OuterOnly: React.FC = () => {
      const outerContext = useOuterContext();
      return <div data-testid="outer-only">{outerContext.value}</div>;
    };
    
    const InnerOnly: React.FC = () => {
      const innerContext = useInnerContext();
      return <div data-testid="inner-only">{innerContext.value}</div>;
    };
    
    render(
      <OuterContextProvider>
        <OuterOnly />
        <InnerContextProvider>
          <InnerOnly />
        </InnerContextProvider>
      </OuterContextProvider>
    );
    
    expect(screen.getByTestId('outer-only')).toHaveTextContent('outer-initial');
    expect(screen.getByTestId('inner-only')).toHaveTextContent('inner-initial');
  });

  it('throws appropriate errors when contexts are missing', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    const InnerOnlyComponent: React.FC = () => {
      useInnerContext(); // Should throw without InnerContextProvider
      return <div>Should not render</div>;
    };
    
    expect(() => {
      render(
        <OuterContextProvider>
          <InnerOnlyComponent />
        </OuterContextProvider>
      );
    }).toThrow('useInnerContext must be used within InnerContextProvider');
    
    consoleError.mockRestore();
  });
});
```

---

## Best Practices for Context Testing

1. **Test the provider and consumer separately** - Test context logic independently from components that use it
2. **Use wrapper functions** - Create wrapper components for `renderHook` when testing context hooks
3. **Test error boundaries** - Ensure contexts throw appropriate errors when used outside providers
4. **Test function stability** - Verify that context functions don't cause unnecessary re-renders
5. **Mock external dependencies** - Mock APIs, services, and other external dependencies
6. **Test state transitions** - Verify that state changes work correctly through actions/dispatchers
7. **Test concurrent operations** - Ensure contexts handle multiple simultaneous operations correctly
8. **Test persistence** - If contexts persist state, test localStorage or other persistence mechanisms
9. **Test performance** - Ensure contexts don't cause unnecessary re-renders of consumers
10. **Test nested contexts** - Verify that multiple contexts work correctly together

---

**Last Updated**: February 2026
