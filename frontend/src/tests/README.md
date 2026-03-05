# Frontend Testing Documentation

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Testing Stack & Patterns](#testing-stack--patterns)
- [Writing Tests](#writing-tests)
- [Commands & Coverage](#commands--coverage)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Frontend testing for the XFD (CyHy Dashboard) project uses a **mirrored directory structure** where all tests in `frontend/src/tests` exactly match the source code organization.

**Key Principles:**
- Tests mirror source code structure: `src/components/Header/` → `tests/components/Header/`
- Use custom `render()` function from `test-utils` (includes AuthContext, Router, Theme)
- All test files use `.test.tsx` or `.test.ts` (never `.spec.*`)
- Focus on testing user behavior, not implementation details

## Quick Start

**Prerequisites:** Node.js >=20.19.4, React/TypeScript/Vitest knowledge

**Essential Commands:**
```bash
npm install          # Install dependencies
npm test             # Run tests (watch mode)
npm run test:coverage # Generate coverage
```

**Key Resources:**
- [📋 Unit Test Templates](../../../docs/testing/frontend/unit-templates/) - Ready-to-use boilerplate
- [📊 CI Coverage Guidelines](../../../docs/testing/frontend/CI_COVERAGE_GUIDELINES.md) - Detailed coverage info

## Testing Stack & Patterns

**Framework:** Vitest ^3.2.4 + jsdom ^26.1.0 + React Testing Library ^14.3.1

**Standardized Imports:**
```typescript
// ✅ Test utilities (includes custom render with providers)
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { testUser, testOrganization } from 'test-utils';

// ✅ Source code - use @ aliases  
import { Header } from '@/components/Header/Header';
import { useVulnScanData } from '@/hooks/useVulnScanData';

// ✅ Mock data - direct imports when needed
import { authCtx } from '@/test-utils/authCtx';

// ❌ AVOID: Direct @testing-library imports (bypasses providers)
// import { render } from '@testing-library/react';
```

**Test Organization:**
```text
frontend/src/tests/
├── components/     # Component tests
├── pages/          # Page component tests  
├── context/        # React Context tests
├── hooks/          # Custom hook tests
└── utils/          # Utility function tests
```

## Writing Tests

**Test Locations:**
- Components: `tests/components/[ComponentPath]/` → `import { Header } from '@/components/Header/Header'`
- Pages: `tests/pages/[PagePath]/` → `import { DomainDetails } from '@/pages/Domain/DomainDetails'`
- Hooks: `tests/hooks/` → `import { useVulnScanData } from '@/hooks/useVulnScanData'`
- Utils: `tests/utils/` → `import { formatDate } from '@/utils/dateUtils'`

**Basic Test Structure:**
```typescript
import { render, screen, fireEvent, waitFor } from 'test-utils';
import { testUser, testOrganization } from 'test-utils';
import { Header } from '@/components/Header/Header';

describe('Header component', () => {
  it('renders user name when authenticated', () => {
    render(<Header />, { 
      authContext: { user: testUser, isAuthenticated: true } 
    });
    expect(screen.getByText(testUser.fullName)).toBeInTheDocument();
  });

  it('handles user interactions', async () => {
    const onSubmit = vi.fn();
    render(<Form onSubmit={onSubmit} />);
    
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
  });
});
```

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

- **Unit Tests**: Individual components, hooks, utilities (Vitest)
- **Integration Tests**: Multiple components working together (Playwright)
- **End-to-End Tests**: Complete user workflows across full application (Playwright)
- **Snapshot Tests**: Component rendering consistency (Vitest)

## Coverage & CI Integration

### Quick Coverage Commands

```bash
# Generate coverage report (recommended)
npm run test:coverage

# View HTML coverage report
npm run test:coverage && open coverage/index.html
```

### Coverage Thresholds

The project maintains **automatic coverage thresholds** that prevent regression. These thresholds are automatically updated by the CI system when coverage improves:

- **Lines**: Percentage of executable code lines that are covered by tests
- **Statements**: Percentage of individual code statements that have been executed during testing
- **Functions**: Percentage of functions/methods that have been called during test execution
- **Branches**: Percentage of conditional branches (if/else, switch cases, etc.) that have been tested

> **📊 Coverage Enforcement**: These thresholds are automatically maintained by the CI system. When coverage improves, thresholds increase to prevent future regression. Current thresholds are visible in the CI configuration and coverage reports.

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

Integration tests verify how multiple components work together within the frontend application. These tests are handled by **Playwright** alongside end-to-end tests.

#### End-to-End Tests

End-to-end tests validate complete user workflows across the entire application (frontend + backend + database). These tests are handled by **Playwright** in a separate test suite.

## Troubleshooting

**Common Issues:**

| Problem | Solution |
|---------|----------|
| "Cannot read property of undefined" | Use `import { render } from 'test-utils'` not `@testing-library/react` |
| Mock data not found | Use `import { testUser } from 'test-utils'` or `import { authCtx } from '@/test-utils/authCtx'` |
| Theme/Provider errors | Custom render includes providers automatically |
| Snapshot mismatches | Run `npm test -- --update` after reviewing changes |
| Coverage issues | Use `npm test -- --coverage --run --exclude="**/problematicFile.test.ts"` |

**Quick Fixes:**
```bash
# Clear cache and reinstall
rm -rf coverage/ node_modules/.vite/
npm ci

# Debug specific tests  
npm test -- --reporter=verbose path/to/test.test.tsx

# Check coverage details
npm run test:coverage && open coverage/index.html
```

**External Resources:**
- [Vitest Documentation](https://vitest.dev/)
- [Testing Library Best Practices](https://testing-library.com/docs/guiding-principles)
- [React Testing Library Documentation](https://testing-library.com/docs/react-testing-library/intro/)

---

**Last Updated**: March 2026
