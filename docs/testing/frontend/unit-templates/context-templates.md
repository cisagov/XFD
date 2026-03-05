# Context Test Templates

General patterns for testing React Context providers and consumers in the XFD frontend application.

## Basic Context Provider Template

```tsx
import { render, screen } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { YourContextProvider, useYourContext } from '@/contexts/YourContext';

// Test component to consume context
const TestConsumer = () => {
  const context = useYourContext();
  return (
    <div>
      <span data-testid="value">{context.value}</span>
      <span data-testid="loading">{context.loading.toString()}</span>
    </div>
  );
};

describe('YourContextProvider', () => {
  it('provides default values', () => {
    render(
      <YourContextProvider>
        <TestConsumer />
      </YourContextProvider>
    );
    
    expect(screen.getByTestId('value')).toHaveTextContent('default');
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
  });

  it('provides custom initial values', () => {
    const initialValue = { value: 'custom', loading: true };
    
    render(
      <YourContextProvider initialValue={initialValue}>
        <TestConsumer />
      </YourContextProvider>
    );
    
    expect(screen.getByTestId('value')).toHaveTextContent('custom');
    expect(screen.getByTestId('loading')).toHaveTextContent('true');
  });
});
```

## Context with Actions Template

```tsx
import { render, screen, fireEvent } from 'test-utils';
import { describe, expect, it } from 'vitest';
import { YourContextProvider, useYourContext } from '@/contexts/YourContext';

const TestComponent = () => {
  const { value, setValue, reset } = useYourContext();
  
  return (
    <div>
      <span data-testid="value">{value}</span>
      <button onClick={() => setValue('updated')}>Update</button>
      <button onClick={reset}>Reset</button>
    </div>
  );
};

describe('YourContext with actions', () => {
  it('updates value when action is called', () => {
    render(
      <YourContextProvider>
        <TestComponent />
      </YourContextProvider>
    );
    
    fireEvent.click(screen.getByText('Update'));
    
    expect(screen.getByTestId('value')).toHaveTextContent('updated');
  });

  it('resets value when reset is called', () => {
    render(
      <YourContextProvider>
        <TestComponent />
      </YourContextProvider>
    );
    
    fireEvent.click(screen.getByText('Update'));
    fireEvent.click(screen.getByText('Reset'));
    
    expect(screen.getByTestId('value')).toHaveTextContent('default');
  });
});
```

## Context Hook Error Handling

```tsx
import React from 'react';
import { renderHook } from 'test-utils';
import { describe, expect, it, vi } from 'vitest';
import { useYourContext } from '@/contexts/YourContext';

describe('useYourContext error handling', () => {
  it('throws error when used outside provider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      renderHook(() => useYourContext());
    }).toThrow('useYourContext must be used within YourContextProvider');
    
    consoleError.mockRestore();
  });
});
```

## Key Patterns

### Testing Providers
- Create test components to consume context
- Test default values and custom initial values
- Use `data-testid` for reliable element selection

### Testing Context Actions
- Test state updates through context actions
- Verify side effects of context operations
- Test action combinations and sequences

### Error Handling
- Test hook usage outside provider
- Suppress console.error during error tests
- Verify appropriate error messages

### With Authentication
- Use existing auth context from `test-utils`
- Test context behavior with different auth states
- Mock authentication-dependent operations

---

**Last Updated**: March 2026
