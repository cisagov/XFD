# Frontend Testing Documentation

## Table of Contents

- [Overview](#overview)
- [Quick Start for New Developers](#quick-start-for-new-developers)
- [Design Principles](#design-principles)
- [Testing Stack](#testing-stack)
- [Current Test Organization](#current-test-organization)
- [Writing Tests](#writing-tests)
- [Running Tests](#running-tests)
- [Coverage & CI Integration](#coverage--ci-integration)
- [Testing Guidelines](#testing-guidelines)
- [XFD-Specific Testing Considerations](#xfd-specific-testing-considerations)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

This document provides comprehensive guidance for frontend testing in the XFD (CyHy Dashboard) project. It describes the standardized frontend test structure implemented to organize all unit tests in a centralized, maintainable way. All tests are located in `frontend/src/tests` with a **mirrored directory structure** that exactly matches the actual component/page organization.

This documentation serves as the single source of truth for frontend testing standards, practices, and guidelines within the XFD project, ensuring consistency and quality across the development team.

## Quick Start for New Developers

### Prerequisites
- Node.js >=20.19.4
- Basic knowledge of React, TypeScript, and testing concepts
- Familiarity with React Testing Library patterns

### Getting Started
1. **Install dependencies**: `npm install`
2. **Run tests**: `npm test` (starts in watch mode)
3. **Generate coverage**: `npm run test:coverage`
4. **Read this documentation** thoroughly before writing your first test
5. **Use the unit test templates**: Check out [📋 Unit Test Templates](../../../docs/testing/frontend/unit-templates/) for ready-to-use boilerplate code
6. **Review existing tests** in `src/tests/` to understand project patterns

### Key Concepts
- Tests mirror the exact source code directory structure
- Use custom `render()` function from `test-utils` for consistent setup
- All test files use `.test.tsx` or `.test.ts` extension (never `.spec.*`)
- Focus on testing user behavior, not implementation details

## Design Principles

### Mirrored Directory Structure

The test structure **exactly mirrors** the actual source code organization:

```text
src/components/Header/ ↔ tests/components/Header/
src/pages/Domain/      ↔ tests/pages/Domain/
src/hooks/             ↔ tests/hooks/
```

### Benefits of This Approach
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
- **Mock data exports** for comprehensive testing scenarios:
  - `testUser` - Mock authenticated user with roles and permissions
  - `testOrganization` - Mock organization data with domains and settings
  - Additional mock data available in individual files (see below)
- **Navigation utilities** for testing routing and navigation behavior
- **Keyboard interaction utilities** for accessibility testing
- **Re-exports** of all testing-library functions for convenient imports

**Recommended Import Patterns:**
```typescript
// ✅ PREFERRED: Use test-utils for everything (includes custom render)
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { testUser, testOrganization } from 'test-utils';

// ⚠️ CURRENT MIXED USAGE (needs standardization):
// Some tests use: 'test-utils/test-utils'
// Some tests use: '@/test-utils/test-utils' 
// Some tests use: relative paths like '../../../test-utils/test-utils'

// ❌ AVOID: Direct @testing-library imports (bypasses custom providers)
// import { render } from '@testing-library/react'; // Don't do this
```

**Available Mock Data:**
```typescript
// Main exports from test-utils index (RECOMMENDED)
import { 
  testUser, 
  testOrganization,
  makeDomain,
  makeDomainResponse,
  makeVuln,
  makeVulnResponse
} from 'test-utils';

// Additional mock data (direct imports when needed)
import { authCtx } from '@/test-utils/authCtx';
import { mockDomains } from '@/test-utils/searchDomains';
import { mockIPs } from '@/test-utils/searchIPs';
import { testRole } from '@/test-utils/role';
```

### Configuration

- **Main config**: `vite.config.mts`
- **Setup file**: `src/setupTests.ts`
- **Environment**: jsdom for DOM testing

## Current Test Organization

All tests are centralized in `frontend/src/tests/` with the following structure:

```text
frontend/src/tests/
├── components/                    # Component tests
│   ├── Dashboard/                 # Dashboard-related components
│   ├── DataGrid/                  # Data grid components and utilities
│   ├── Dialog/                    # Modal and dialog components
│   ├── FilterDrawer/              # Search and filter drawer components
│   ├── Gates/                     # Access control and gate components
│   ├── Header/                    # Navigation and header components
│   ├── Routes/                    # Routing and route guard components
│   ├── UpdateUserStateForm/       # User state management forms
│   ├── govBanner.test.tsx         # Root-level components
│   ├── layout.test.tsx            # Layout components
│   └── __snapshots__/             # Automatically generated snapshot files
├── pages/                         # Page component tests
│   ├── AdminTools/                # Administrative functionality
│   ├── Domain/                    # Individual domain pages
│   ├── Domains/                   # Domain listing and management
│   ├── LoginGovCallback/          # Authentication callback handling
│   ├── Organizations/             # Organization management pages
│   ├── Settings/                  # Application settings
│   ├── UserRegistration/          # User registration workflows
│   ├── Users/                     # User management pages
│   ├── Vulnerabilities/           # Vulnerability listing pages
│   └── VulnerabilityScanDash/     # Vulnerability dashboard and analytics
├── context/                       # React Context tests
│   ├── authCtx.test.tsx          # Authentication context
│   ├── FilterDrawerContextProvider.test.tsx
│   ├── NavigationContextProvider.test.tsx
│   ├── SavedSearchContextProvider.test.tsx
│   └── SearchProvider.test.tsx    # Various context providers
├── hooks/                         # Custom hook tests
│   ├── useAddUserToOrganization.test.ts
│   ├── useApiTelemetry.test.ts
│   ├── useGetApi.test.ts
│   ├── usePostApi.test.ts         # API-related hooks
│   ├── usePersistentState.test.tsx
│   ├── useUserActivityTimeout.test.ts
│   └── [other-hooks].test.ts      # Additional custom hooks
└── utils/                         # Utility function tests
    ├── buildOrgFilters.test.ts
    ├── dateUtils.test.ts
    ├── stringUtils.test.ts
    ├── transformVulnScanData.test.ts
    └── [other-utils].test.ts       # Various utility functions
```

### Key Organization Principles

- **Mirrored Structure**: Each directory corresponds to its source code counterpart
- **Logical Grouping**: Tests are grouped by functionality (components, pages, hooks, utils, context)
- **Consistent Naming**: All test files follow the `.test.tsx` or `.test.ts` convention
- **Automatic Snapshots**: Snapshot files are automatically managed in `__snapshots__/` directories

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

```typescript
// Source code imports (using relative paths)
// Component tests: '../../../components/[ComponentPath]/ComponentName'
// Page tests: '../../../pages/[PagePath]/PageName'  
// Hook tests: '../../hooks/hookName'
// Utility tests: '../../utils/utilityName'

// Alternative: Use path aliases (mixed usage in current codebase)
import { DomainDetails } from '@/pages/Domain/DomainDetails';
import { useVulnScanData } from '@/hooks/useVulnScanData';
```

**Test Utilities (Recommended Pattern):**

```typescript
// ✅ RECOMMENDED: Import from test-utils index
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { testUser, testOrganization } from 'test-utils';

// 📝 NOTE: Some existing tests use alternative patterns:
// - 'test-utils/test-utils' 
// - '@/test-utils/test-utils'
// - Relative paths to test-utils files
```

**Context and Provider Imports:**

```typescript
// Context imports (common patterns in existing tests)
import { useAuthContext } from 'context';
import { AuthContextProvider } from 'context/AuthContextProvider';

// Alternative absolute path (also used)
import { useAuthContext } from '@/context/AuthContext';
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

- **Provider**: istanbul (detailed, accurate)
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

## Coverage & CI Integration

### Quick Coverage Commands

```bash
# Generate coverage report (recommended)
npm run test:coverage

# View HTML coverage report
npm run test:coverage && open coverage/index.html
```

### Coverage Thresholds

The project maintains **automatic coverage thresholds** that prevent regression:

- **Lines**: ~46.5% (auto-updated in CI)
- **Statements**: ~46.0% (auto-updated in CI) 
- **Functions**: ~41.5% (auto-updated in CI)
- **Branches**: ~34.6% (auto-updated in CI)

> **📊 Coverage Enforcement**: These thresholds are automatically maintained by the CI system. When coverage improves, thresholds increase to prevent future regression.

### CI Integration

- **GitHub Actions**: Runs coverage on all PRs and pushes
- **Coveralls**: Tracks coverage history and trends 
- **Quality Gates**: PRs must meet coverage thresholds to merge
- **Auto-Update**: Thresholds automatically increase with improvements

### Comprehensive Coverage Documentation

For complete coverage guidelines, CI configuration, troubleshooting, and advanced commands, see:

📋 **[CI Coverage & Reporting Guidelines](../../../docs/testing/frontend/CI_COVERAGE_GUIDELINES.md)**

This document covers:
- Detailed threshold configuration and targets
- Complete CI pipeline integration
- Local development and analysis commands  
- Coverage report formats and interpretation
- Quality gates and failure scenarios
- Integration with external coverage services

## Testing Guidelines

### Test Types

#### Unit Tests

Test individual components, hooks, or utilities in isolation.

```typescript
// Component unit test
describe('Header component', () => {
  it('renders user name when authenticated', () => {
    render(<Header />, { authContext: { user: testUser } });
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

Use Playwright for end-to-end testing (covered in separate documentation).

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

## XFD-Specific Testing Considerations

### Authentication Testing

> **Note**: The XFD application is transitioning away from AWS Amplify authentication (legacy). Current authentication components may still reference Amplify patterns, but new development should follow the updated authentication approach.

When testing components that depend on authentication state:

```typescript
// Test authenticated state
render(<Component />, {
  authContext: {
    user: testUser,
    isAuthenticated: true,
    currentOrganization: testOrganization
  }
});

// Test unauthenticated state
render(<Component />, {
  authContext: {
    user: null,
    isAuthenticated: false,
    currentOrganization: null
  }
});
```

### Material-UI Component Testing

XFD uses Material-UI extensively. Key considerations:

- **Data Grid Testing**: Use `getByRole('grid')` and `getAllByRole('gridcell')`
- **Modal Testing**: Ensure proper cleanup with `cleanup()` after modal tests
- **Theme Testing**: Components are wrapped with `CFThemeProvider` automatically in test utils
- **Loading States**: Many MUI components have built-in loading states to test

```typescript
// Testing MUI DataGrid
it('displays data in grid format', () => {
  render(<DataGridComponent data={testData} />);
  
  expect(screen.getByRole('grid')).toBeInTheDocument();
  expect(screen.getAllByRole('gridcell')).toHaveLength(expectedCellCount);
});
```

### API Testing Patterns

XFD components often integrate with AWS services. Mock API calls appropriately:

```typescript
// Mock API utilities (already available in test-utils)
import { vi } from 'vitest';

// Mock successful API response
const mockApiCall = vi.fn().mockResolvedValue({
  data: testData,
  status: 200
});

// Mock API error
const mockApiError = vi.fn().mockRejectedValue(new Error('API Error'));
```

### Router Testing

XFD uses React Router v5. Test navigation and route-dependent components:

```typescript
// Test component with specific route
render(<Component />, {
  initialHistory: ['/domains/123']
});

// Test navigation behavior
const linkElement = screen.getByRole('link', { name: /view details/i });
fireEvent.click(linkElement);
// Assert navigation occurred
```

### Organization Context Testing

Many XFD components depend on the current organization context:

```typescript
// Test with specific organization
render(<Component />, {
  authContext: {
    currentOrganization: testOrganization,
    user: testUser
  }
});
```

### Vulnerability Data Testing

When testing vulnerability-related components, use the provided test utilities:

```typescript
import { makeVulnResponse } from 'test-utils/vulnerabilities';

const mockVulnData = makeVulnResponse(5); // Creates 5 mock vulnerabilities
```

### Domain Testing

For domain-related components:

```typescript
import { testDomains } from 'test-utils/domains';

render(<DomainsTable domains={testDomains} />);
```

## Current Inconsistencies & Migration Notes

⚠️ **The XFD test suite is currently in a mixed state with several patterns that need standardization.**

### Import Pattern Inconsistencies

**Current Mixed Usage (found in existing tests):**
```typescript
// Pattern 1: Direct test-utils import (PREFERRED)
import { render, screen } from 'test-utils';

// Pattern 2: Explicit test-utils file path  
import { render, screen } from 'test-utils/test-utils';

// Pattern 3: Absolute path with alias
import { render, screen } from '@/test-utils/test-utils';

// Pattern 4: Relative paths
import { render, screen } from '../../../test-utils/test-utils';

// Pattern 5: Direct @testing-library imports (AVOID - bypasses providers)
import { render, screen } from '@testing-library/react';
```

**Recommendation**: Standardize on Pattern 1 (`import { render, screen } from 'test-utils'`) for all new tests.

### Mock Data Access Patterns

**Current Mixed Usage:**
```typescript
// Available through main index (PREFERRED)
import { testUser, testOrganization } from 'test-utils';

// Direct file imports (currently necessary for some mocks)
import { authCtx } from '@/test-utils/authCtx';
import { makeVulnResponse } from '@/test-utils/vulnerabilities';
import { mockDomains } from '@/test-utils/searchDomains';

// Relative path imports (found in some existing tests)
import { testUser } from '../../../test-utils/user';
```

**Recommendation**: Use main index exports when available, direct imports when necessary, avoid relative paths.

### Testing Library Import Issues

Some existing tests import directly from `@testing-library/react`, which bypasses the custom render function and its pre-configured providers. This can cause tests to fail that depend on AuthContext, Router, or Theme providers.

**Migration Priority**: 
1. **High**: Tests that render components requiring AuthContext, Router, or Theme
2. **Medium**: Tests using custom test utilities or mock data
3. **Low**: Simple utility function tests that don't need providers

## Best Practices

### General Testing Principles

1. **Test user behavior, not implementation**: Focus on what users see and do rather than internal component state
2. **Write descriptive test names**: Use clear, specific descriptions that explain the expected behavior
3. **Follow Arrange-Act-Assert pattern**: Structure tests with clear setup, action, and verification phases
4. **Use semantic queries**: Prefer `getByRole`, `getByLabelText`, `getByText` over `getByTestId`
5. **Test error states**: Always include tests for error scenarios and edge cases

### XFD-Specific Best Practices

#### Accessibility Testing
- Use semantic HTML elements and ARIA attributes
- Test keyboard navigation with `Tab`, `Enter`, and arrow keys
- Verify screen reader compatibility with proper labels and descriptions
- Test color contrast and visual indicators

```typescript
// Test keyboard navigation
it('allows keyboard navigation through table rows', () => {
  render(<DataTable data={testData} />);
  
  const firstRow = screen.getAllByRole('row')[1]; // Skip header
  firstRow.focus();
  
  fireEvent.keyDown(firstRow, { key: 'ArrowDown' });
  expect(screen.getAllByRole('row')[2]).toHaveFocus();
});
```

#### Security Testing Considerations
- **Input Sanitization**: Test that user inputs are properly sanitized
- **XSS Prevention**: Verify that dynamic content doesn't execute scripts
- **Data Exposure**: Ensure sensitive data isn't exposed in test snapshots
- **Authentication State**: Test unauthorized access scenarios

```typescript
// Test input sanitization
it('sanitizes malicious input', () => {
  const maliciousInput = '<script>alert("xss")</script>';
  render(<SearchInput value={maliciousInput} />);
  
  // Should not contain script tags
  expect(screen.queryByText('<script>')).not.toBeInTheDocument();
});
```

#### Performance Testing Guidelines
- **Large Data Sets**: Test component behavior with large amounts of data
- **Loading States**: Verify loading indicators appear and disappear appropriately
- **Memory Leaks**: Ensure proper cleanup in `useEffect` hooks
- **Virtualization**: Test virtual scrolling components with mock data

#### Data Integrity Testing
- **Validation**: Test form validation with various input scenarios
- **Data Transformation**: Verify data is correctly formatted for display
- **Sorting/Filtering**: Test table operations maintain data consistency
- **State Management**: Ensure state updates don't cause data corruption

### Code Quality Standards

#### Test Organization
- Group related tests using `describe` blocks
- Use consistent naming conventions across all test files
- Keep test files focused on single components or utilities
- Maintain test file size under 500 lines when possible

#### Mock Strategy
- Mock external dependencies (APIs, third-party libraries)
- Use `vi.mock()` for module-level mocking
- Create reusable mock factories for complex objects
- Reset mocks between tests to prevent interference

```typescript
// Reusable mock factory
export const createMockApiResponse = (overrides = {}) => ({
  data: [],
  total: 0,
  page: 1,
  status: 'success',
  ...overrides
});
```

#### Snapshot Testing Guidelines
- Use snapshots sparingly for complex UI structures
- Avoid snapshots for frequently changing components
- Update snapshots only when intentional changes are made
- Use descriptive snapshot names that explain the component state

### Continuous Improvement
- **Regular Review**: Periodically review and refactor tests
- **Coverage Goals**: Aim for meaningful coverage, not just high percentages
- **Team Standards**: Follow established team conventions and patterns
- **Documentation**: Keep test documentation up-to-date with code changes

## Troubleshooting

## Troubleshooting

### Common Issues and Solutions

#### Import Path Errors
**Problem**: Import path errors when running tests after restructuring
**Solution**: Ensure relative paths are correct for the mirrored structure

```typescript
// ❌ Wrong - old flat structure
import { Component } from '../../Component';

// ✅ Correct - mirrored structure
import { Component } from '../../../components/Header/Component';
```

#### Missing Test Utilities
**Problem**: `render` function or mock data not found
**Solution**: Import from the centralized test-utils

```typescript
// ✅ Correct imports
import { render, screen, fireEvent } from 'test-utils';
import { testUser } from 'test-utils';
```

#### Authentication Context Issues
**Problem**: Components fail because they expect authentication context
**Solution**: Use the custom `render()` function with proper auth context

```typescript
// ✅ Provide auth context
render(<Component />, {
  authContext: {
    user: testUser,
    isAuthenticated: true
  }
});
```

#### Material-UI Theme Errors
**Problem**: MUI components throw theme-related errors
**Solution**: The custom render function includes `CFThemeProvider` automatically

```typescript
// ✅ Theme is provided automatically
import { render } from 'test-utils';
render(<MuiComponent />); // Theme provider included
```

#### Router Context Missing
**Problem**: Components using `useHistory` or `useLocation` fail
**Solution**: Provide routing context with `initialHistory`

```typescript
// ✅ Provide routing context
render(<Component />, {
  initialHistory: ['/current/path']
});
```

#### Async Testing Issues
**Problem**: Tests fail intermittently with async operations
**Solution**: Use proper async testing patterns

```typescript
// ✅ Wait for async operations
await waitFor(() => {
  expect(screen.getByText('Loaded data')).toBeInTheDocument();
});

// ✅ For user events
await user.click(screen.getByRole('button'));
```

#### Import Pattern Issues
**Problem**: Tests fail with "Cannot read property of undefined" or provider-related errors
**Solutions**:
```typescript
// ❌ This may cause issues if component needs providers
import { render } from '@testing-library/react';

// ✅ Use this instead for components that need AuthContext, Router, Theme
import { render } from 'test-utils';
```

**Problem**: Mock data not found or import errors
**Solutions**:
```typescript
// ✅ Use main index exports when available
import { testUser, makeVuln } from 'test-utils';

// ✅ Use direct imports for non-exported mocks
import { authCtx } from '@/test-utils/authCtx';

// ❌ Avoid relative paths in new tests
// import { testUser } from '../../../test-utils/user';
```

#### Mixed Import Patterns in Existing Tests
**Problem**: Inconsistent imports across the codebase
**Current Status**: The codebase has mixed patterns that need standardization:
- Some tests use `'test-utils'` (preferred)
- Some use `'test-utils/test-utils'` 
- Some use `'@/test-utils/test-utils'`
- Some use direct `@testing-library/react` imports

**For New Tests**: Always use `import { render, screen } from 'test-utils'`

#### Snapshot Mismatches
**Problem**: Snapshot tests fail after component updates
**Solutions**:
- Review changes carefully before updating
- Update snapshots: `npm test -- --update`
- Consider if snapshot is still valuable

```bash
# Update all snapshots
npm test -- --update

# Update specific test snapshots
npm test -- --update components/Header/header.test.tsx
```

#### Coverage Issues
**Problem**: Coverage reports show unexpected results
**Solutions**:
- Exclude problematic test files: `npm test -- --coverage --run --exclude="**/problematicFile.test.ts"`
- Check coverage configuration in `vite.config.mts`
- Verify file paths match coverage include/exclude patterns

#### Mock-Related Issues
**Problem**: Mocks not working as expected
**Solutions**:

```typescript
// ✅ Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks();
});

// ✅ Mock modules properly
vi.mock('../../api/endpoints', () => ({
  fetchData: vi.fn()
}));
```

#### Performance Issues
**Problem**: Tests run slowly or time out
**Solutions**:
- Use `vi.useFakeTimers()` for date/time-dependent tests
- Mock expensive operations
- Reduce test data size
- Consider running tests in parallel

```typescript
// ✅ Mock timers for faster tests
beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});
```

#### Environment Issues
**Problem**: Tests behave differently in different environments
**Solutions**:
- Check Node.js version (requires >=20.19.4)
- Verify jsdom environment is properly configured
- Clear `node_modules` and reinstall if needed
- Check for conflicting global installations

### XFD-Specific Troubleshooting

#### AWS Amplify Mock Issues (Legacy)
> **Note**: Amplify is being phased out. This section applies to legacy components only.
**Problem**: Amplify authentication mocks not working
**Solution**: Ensure proper mock setup in test utilities for legacy components

#### Large Dataset Performance
**Problem**: Tests slow when using real data
**Solution**: Use smaller mock datasets from test-utils

#### MUI DataGrid Issues
**Problem**: DataGrid components cause test failures
**Solution**: DataGrid is configured in Vite config dependencies

### Getting Help

1. **Check existing tests**: Look for similar patterns in the codebase
2. **Review test-utils**: Many common scenarios have helper functions
3. **Check this documentation**: Most common issues are covered here
4. **Team consultation**: Reach out to team members for XFD-specific issues
5. **External resources**: 
   - [Vitest Documentation](https://vitest.dev/)
   - [Testing Library Best Practices](https://testing-library.com/docs/guiding-principles)
   - [React Testing Library Documentation](https://testing-library.com/docs/react-testing-library/intro/)
   - [Common Testing Mistakes](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
   - [Testing JavaScript](https://testingjavascript.com/) - Kent C. Dodds course

### Debugging Tips

- Use `screen.debug()` to see the rendered DOM
- Add `console.log()` statements to understand component state
- Use `--reporter=verbose` for detailed test output
- Run single test files for faster debugging: `npm test -- path/to/test.test.tsx`

**Last Updated**: February 2026
