# Frontend Test Structure Documentation

## Overview

This document describes the standardized frontend test structure implemented to organize all unit tests in a centralized, maintainable way. All tests are now located in `frontend/src/tests` with a **mirrored directory structure** that exactly matches the actual component/page organization.

## Design Principles

### Mirrored Directory Structure
The test structure **exactly mirrors** the actual source code organization:

```
src/components/Header/ ↔ tests/components/Header/
src/pages/Domain/      ↔ tests/pages/Domain/
src/hooks/             ↔ tests/hooks/
```

### Benefits of This Approach:
- **Intuitive Navigation**: Find tests by following the same path as source files
- **Maintainable**: Simple relative import paths, easier to refactor
- **Scalable**: No naming conflicts as the project grows
- **Consistent**: Same organizational patterns throughout the codebase
- **Future-proof**: Component reorganizations automatically reflect in test structure

## Testing Stack

### Framework & Tools
- **Vitest** (`^3.2.4`) - Modern, Vite-native testing framework
- **jsdom** (`^26.1.0`) - Browser environment simulation  
- **@testing-library/react** (`^14.3.1`) - Component testing utilities
- **@testing-library/user-event** (`^13.5.0`) - User interaction simulation
- **@testing-library/jest-dom** (`^6.6.3`) - DOM matchers (toBeInTheDocument, etc.)

### Custom Test Utilities
Located in `src/test-utils/`, these provide:
- **Custom render()** function with pre-configured providers (AuthContext, Router, Theme)
- **Mock data exports** (`testUser`, `testOrganization`)  
- **Re-exports** of all testing-library functions for convenient imports

### Configuration
- **Main config**: `vite.config.mts`
- **Setup file**: `src/setupTests.ts`
- **Environment**: jsdom for DOM testing

## Current Test Organization

All tests are centralized in `frontend/src/tests/` with the following structure:

```
frontend/src/tests/
├── components/                    # Component tests
│   ├── Dialog/
│   │   └── TermsOfUse/
│   │       └── termsOfUse.test.tsx
│   ├── Gates/
│   │   └── vs-dashboard-gate.test.tsx
│   ├── Header/
│   │   └── header.test.tsx
│   ├── Routes/
│   │   └── routeGuard.test.tsx
│   ├── UpdateUserStateForm/
│   │   └── updateUserStateForm.test.tsx
│   ├── govBanner.test.tsx         # Root-level component
│   ├── layout.test.tsx            # Root-level component
│   └── __snapshots__/             # Snapshot files
├── pages/                         # Page component tests
│   ├── Domain/
│   │   └── domainDetails.test.tsx
│   ├── Domains/
│   │   └── domainsTable.test.tsx
│   ├── LoginGovCallback/
│   │   └── loginGovCallback.test.tsx
│   └── Vulnerabilities/
│       └── vulnerabilitiesTable.test.tsx
├── context/                       # Context tests
│   └── authCtx.test.tsx
├── hooks/                         # Custom hook tests
│   ├── usePersistentState.test.tsx
│   ├── useUserActivityTimeout.test.ts
│   └── useVulnScanData.test.ts
├── utils/                         # Utility function tests
│   ├── dateUtils.test.ts
│   └── transformVulnScanData.test.ts
└── types/                         # Type-related tests (future)
```

### Naming Conventions

- **All test files**: Use `.test.tsx` (React components) or `.test.ts` (pure functions/hooks)
- **DO NOT USE `.spec.*`**: Standardized on `.test.*` convention
- **Snapshot files**: Automatically managed by Vitest in `__snapshots__/` directories

## Writing Tests

### Location Guidelines

**Component Tests** → `tests/components/[ComponentPath]/`
```typescript
// For src/components/Header/Header.tsx
// Write tests in: tests/components/Header/header.test.tsx
import { Header } from '../../../components/Header/Header';
```

**Page Tests** → `tests/pages/[PagePath]/`  
```typescript
// For src/pages/Domain/DomainDetails.tsx  
// Write tests in: tests/pages/Domain/domainDetails.test.tsx
import { DomainDetails } from '../../../pages/Domain/DomainDetails';
```

**Hook Tests** → `tests/hooks/`
```typescript
// For src/hooks/useVulnScanData.ts
// Write tests in: tests/hooks/useVulnScanData.test.ts
import { useVulnScanData } from '../../hooks/useVulnScanData';
```

**Utility Tests** → `tests/utils/`
```typescript
// For src/utils/dateUtils.ts
// Write tests in: tests/utils/dateUtils.test.ts
import { formatDate } from '../../utils/dateUtils';
```

### Import Patterns

**Relative Imports from Test Files:**
- Component tests: `'../../../components/[ComponentPath]/ComponentName'`
- Page tests: `'../../../pages/[PagePath]/PageName'`  
- Hook tests: `'../../hooks/hookName'`
- Utility tests: `'../../utils/utilityName'`

**Test Utilities:**
```typescript
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { testUser, testOrganization } from 'test-utils';
```

### Snapshot Testing

- Snapshots are automatically generated in `__snapshots__/` directories alongside test files
- Use descriptive snapshot names: `expect(component).toMatchSnapshot('component-state')`
- Update snapshots with: `npm test -- --update-snapshots`

## Running Tests

### Commands
```bash
# Run all tests (watch mode - default)
npm test

# Run all tests once (no watch mode)
npm test -- --run

# Run specific test file
npm test -- path/to/test.test.tsx

# Run tests excluding specific files
npm test -- --exclude="**/useVulnScanData.test.ts"
npm test -- --exclude="**/problematicFile.test.tsx"

# Run tests with coverage (generates reports)
npm test -- --coverage
npm test -- --coverage --run

# Update snapshots
npm test -- --update
npm test -- -u
```

### Coverage Reports

The project is configured to generate comprehensive test coverage reports:

**Coverage Configuration:**
- **Provider**: v8 (fast, accurate)
- **Reports**: Terminal output + HTML + JSON
- **Output**: `frontend/coverage/` (excluded from git)

**Coverage Commands:**
```bash
# Generate coverage with terminal output
npm test -- --coverage --run

# Exclude failing tests from coverage
npm test -- --coverage --run --exclude="**/useVulnScanData.test.ts"
```

**Coverage Reports Generated:**
- **Terminal**: Immediate coverage summary in console
- **HTML Report**: `coverage/index.html` - Interactive, detailed coverage explorer
- **JSON Report**: `coverage/coverage-final.json` - Machine-readable data for CI/CD

**Coverage Exclusions:**
- Test files (`**/*.{test,spec}.{js,ts,jsx,tsx}`)
- Setup files (`src/setupTests.ts`)
- Test utilities (`**/test-utils/**`)
- Node modules and build artifacts

### Test Categories
- **Unit Tests**: Individual components, hooks, utilities
- **Integration Tests**: Multiple components working together  
- **Snapshot Tests**: Component rendering consistency

## Testing Guidelines

### Test Types

#### Unit Tests
Test individual components, hooks, or utilities in isolation.
```typescript
// Component unit test
describe('Header component', () => {
  it('renders user name when authenticated', () => {
    render(<Header />, { user: testUser });
    expect(screen.getByText(testUser.fullName)).toBeInTheDocument();
  });
});

// Hook unit test  
describe('useVulnScanData', () => {
  it('returns initial data when orgId is empty', () => {
    const { result } = renderHook(() => useVulnScanData(''));
    expect(result.current.data).toEqual(InitialVSData);
  });
});
```

#### Integration Tests
Test multiple components or systems working together.
```typescript
describe('Vulnerabilities page integration', () => {
  it('loads and displays vulnerability data', async () => {
    const mockData = makeVulnResponse(5);
    apiPost.mockResolvedValue(mockData);
    
    render(<Vulnerabilities />);
    
    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument();
    });
  });
});
```

#### End-to-end Tests
**Use Playwright**

### Best Practices

1. **Descriptive test names**: Use clear, specific descriptions
2. **Arrange-Act-Assert**: Structure tests with clear setup, action, and verification
3. **Use test utilities**: Leverage custom render functions and mock data
4. **Test user behavior**: Focus on what users see and do, not implementation details
5. **Snapshot sparingly**: Use for complex UI structures, not simple components
6. **Mock external dependencies**: Use vi.mock() for API calls, external libraries

### Common Patterns

```typescript
// Testing user interactions
import { fireEvent, waitFor } from 'test-utils';

it('submits form when button clicked', async () => {
  const onSubmit = vi.fn();
  render(<Form onSubmit={onSubmit} />);
  
  fireEvent.click(screen.getByRole('button', { name: /submit/i }));
  
  await waitFor(() => {
    expect(onSubmit).toHaveBeenCalled();
  });
});

// Testing async operations
it('shows loading state during API call', async () => {
  const slowApi = vi.fn().mockImplementation(() => 
    new Promise(resolve => setTimeout(resolve, 100))
  );
  
  render(<Component api={slowApi} />);
  
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
  
  await waitFor(() => {
    expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
  });
});
```

## Troubleshooting

### Common Issues

**Import path errors**: Ensure relative paths are correct for the new structure
```typescript
// ❌ Wrong - old flat structure
import { Component } from '../../Component';

// ✅ Correct - mirrored structure  
import { Component } from '../../../components/Header/Component';
```

**Missing test utilities**: Import from the centralized test-utils
```typescript
// ✅ Correct imports
import { render, screen, fireEvent } from 'test-utils';
import { testUser } from 'test-utils';
```

**Snapshot mismatches**: Update snapshots after structural changes
```bash
npm test -- --update
npm test -- -u
```

**Failing tests blocking coverage**: Exclude problematic test files
```bash
# Skip specific failing test file
npm test -- --coverage --run --exclude="**/useVulnScanData.test.ts"

# Skip multiple test files
npm test -- --exclude="**/file1.test.ts" --exclude="**/file2.test.tsx"
```

**Context/Provider issues**: Some tests may fail due to missing context providers
- Check if components require AuthContext, ThemeProvider, or Router
- Use the custom `render()` function from `test-utils` which includes providers
- For hook tests, ensure proper context setup with `renderHook()`
**Last Updated**: November 2025
