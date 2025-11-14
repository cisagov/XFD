# Frontend Test Structure Standardization Plan

**Ticket:** CRASM-3382 - Standardize frontend unit test file organization  
**Branch:** jsalinas-standardize-frontend-test-structure-CRASM-3382  

## Overview

This document outlines the plan to restructure frontend unit tests from scattered `__tests__` directories into a centralized `frontend/src/tests` folder with **mirrored directory structure** matching the actual component/page organization and consistent naming conventions.

## Strategy Decision: Mirror Component Structure

After initial implementation, we've decided to **mirror the actual component/page directory structure** in tests for better maintainability:

### Benefits of Mirrored Structure:
- **Intuitive navigation**: Easy to find tests by following the same path as components
- **Maintainable import paths**: Simple relative imports (e.g., `../ComponentName`)
- **Scalable**: Avoids naming conflicts as project grows
- **Future-proof**: Component reorganizations are reflected in test structure

## Current Test Structure Analysis

### Current Testing Stack

**Testing Framework:** **Vitest** (`^3.2.4`) - Modern, Vite-native testing framework
- Fully migrated from Jest to Vitest
- Uses jsdom environment for DOM simulation
- Configuration in `vite.config.mts`

**Testing Libraries in Active Use:**
- **@testing-library/react** (`^14.3.1`) - **Heavily used** for component testing
- **@testing-library/user-event** (`^13.5.0`) - User interaction simulation  
- **@testing-library/jest-dom** (`^6.6.3`) - DOM matchers (toBeInTheDocument, etc.)
- **jsdom** (`^26.1.0`) - Browser environment simulation
- **Custom test-utils** - Wrapper utilities that provide:
  - Custom `render()` function with context providers (AuthContext, Router, Theme)
  - Mock data exports (`testUser`, `testOrganization`)
  - Re-exports of all testing-library functions

**Usage Evidence:**
- Component tests extensively use `render()`, `screen`, `findBy*`, `waitFor`
- All React component tests follow React Testing Library patterns
- Tests import from both direct `@testing-library/react` and custom `test-utils`
- No legacy testing patterns found (no Enzyme, no Jest-specific imports)

### Existing Test Locations

The tests are currently distributed across multiple `__tests__` directories:

1. **`/src/context/__tests__/`**
   - `authCtx.spec.tsx`

2. **`/src/utils/__tests__/`**
   - `transformVulnScanData.test.ts` ✅ (correct naming)
   - `dateUtils.test.ts` ✅ (correct naming)

3. **`/src/components/__tests__/`**
   - `domainsTable.spec.tsx`
   - `layout.spec.tsx`
   - `routeGuard.spec.tsx`
   - `header.spec.tsx`
   - `govBanner.spec.tsx`
   - `updateUserStateForm.spec.tsx`
   - `domainDetails.spec.tsx`
   - `vulnerabilitiesTable.spec.tsx`
   - `__snapshots__/` directory with multiple snapshot files

4. **`/src/components/Gates/__tests__/`**
   - `vs-dashboard-gate.spec.tsx`

5. **`/src/components/Dialog/TermsOfUse/__tests__/`**
   - `termsOfUse.spec.tsx`
   - `__snapshots__/termsOfUse.spec.tsx.snap`

6. **`/src/components/FilterDrawer/`** (not in __tests__ folder)
   - `AutoCompletedResults.spec.tsx`

7. **`/src/hooks/__tests__/`** (incorrect file extensions)
   - `usePersistentState.tsx` ❌ (should be .test.tsx)
   - `useUserActivityTimeout.ts` ❌ (should be .test.ts)
   - `useVulnScanData.ts` ❌ (should be .test.ts)

8. **`/src/pages/LoginGovCallback/__tests__/`**
   - `loginGovCallback.spec.tsx`

### Current Issues Identified

1. **Inconsistent naming conventions**: Mix of `.spec.tsx`, `.test.ts`, and plain `.tsx/.ts` files
2. **Scattered organization**: Tests spread across different `__tests__` directories
3. **Inconsistent structure**: Some tests in `__tests__` folders, others directly in component folders
4. **Non-standard file extensions**: Hook tests don't follow naming conventions
5. **⚠️ Incomplete Jest → Vitest migration**: Hook tests still use Jest APIs (`jest.spyOn`, `jest.mocked`, etc.) and import missing `jest-date-mock` dependency

## Target Structure

### New Centralized Organization

```
frontend/src/tests/
├── components/
│   ├── Dialog/
│   │   └── TermsOfUse/
│   │       └── termsOfUse.test.tsx (from Dialog/TermsOfUse/__tests__/)
│   ├── Gates/
│   │   └── vs-dashboard-gate.test.tsx (from Gates/__tests__/)
│   ├── Header/
│   │   └── header.test.tsx (from components/__tests__/)
│   ├── Routes/
│   │   └── routeGuard.test.tsx (from components/__tests__/)
│   ├── UpdateUserStateForm/
│   │   └── updateUserStateForm.test.tsx (from components/__tests__/)
│   ├── govBanner.test.tsx (from components/__tests__/ - root level component)
│   ├── layout.test.tsx (from components/__tests__/ - root level component)
│   └── __snapshots__/
│       └── (snapshots will be generated in appropriate subdirectories)
├── pages/
│   ├── Domain/
│   │   └── domainDetails.test.tsx (MOVED from components/__tests__/)
│   ├── Domains/
│   │   └── domainsTable.test.tsx (MOVED from components/__tests__/)
│   ├── Vulnerabilities/
│   │   └── vulnerabilities.test.tsx (existing from pages/__tests__/)
│   │   └── vulnerabilitiesTable.test.tsx (MOVED from components/__tests__/)
│   └── (other page test directories as needed)
├── context/
│   └── authCtx.test.tsx
├── hooks/
│   ├── usePersistentState.test.tsx
│   ├── useUserActivityTimeout.test.ts
│   └── useVulnScanData.test.ts
├── utils/
│   ├── transformVulnScanData.test.ts
│   └── dateUtils.test.ts
└── types/
```

## Migration Steps

### Step 1: Create Centralized Test Directory Structure

Create the new directory structure:
```bash
mkdir -p frontend/src/tests/{components,pages,context,hooks,utils,types}
mkdir -p frontend/src/tests/components/{AuthRoute,Dashboard,DataGrid,Dialog/TermsOfUse,FilterDrawer,FindingsLibrary,Gates,Header,Layout,Logs,Metrics,Notifications,Routes,ScanForm,UpdateUserStateForm,__snapshots__}
mkdir -p frontend/src/tests/pages/{AdminTools,Domain,Domains,LoginGovCallback,Organization,Organizations,Scans,Settings,Users,Vulnerabilities,VulnerabilityScanDash}
```

### Step 2: File Migration Map

| Current Location | New Location | Rename Required |
|------------------|--------------|-----------------|
| `context/__tests__/authCtx.spec.tsx` | `tests/context/authCtx.test.tsx` | ✅ spec→test |
| `utils/__tests__/transformVulnScanData.test.ts` | `tests/utils/transformVulnScanData.test.ts` | ❌ |
| `utils/__tests__/dateUtils.test.ts` | `tests/utils/dateUtils.test.ts` | ❌ |
| `components/__tests__/domainsTable.spec.tsx` | `tests/components/domainsTable.test.tsx` | ✅ spec→test |
| `components/__tests__/layout.spec.tsx` | `tests/components/layout.test.tsx` | ✅ spec→test |
| `components/__tests__/routeGuard.spec.tsx` | `tests/components/routeGuard.test.tsx` | ✅ spec→test |
| `components/__tests__/header.spec.tsx` | `tests/components/header.test.tsx` | ✅ spec→test |
| `components/__tests__/govBanner.spec.tsx` | `tests/components/govBanner.test.tsx` | ✅ spec→test |
| `components/__tests__/updateUserStateForm.spec.tsx` | `tests/components/updateUserStateForm.test.tsx` | ✅ spec→test |
| `components/__tests__/domainDetails.spec.tsx` | `tests/components/domainDetails.test.tsx` | ✅ spec→test |
| `components/__tests__/vulnerabilitiesTable.spec.tsx` | `tests/components/vulnerabilitiesTable.test.tsx` | ✅ spec→test |
| `components/Gates/__tests__/vs-dashboard-gate.spec.tsx` | `tests/components/Gates/vs-dashboard-gate.test.tsx` | ✅ spec→test |
| `components/Dialog/TermsOfUse/__tests__/termsOfUse.spec.tsx` | `tests/components/Dialog/TermsOfUse/termsOfUse.test.tsx` | ✅ spec→test |
| `components/FilterDrawer/AutoCompletedResults.spec.tsx` | `tests/components/FilterDrawer/AutoCompletedResults.test.tsx` | ✅ spec→test |
| `hooks/__tests__/usePersistentState.tsx` | `tests/hooks/usePersistentState.test.tsx` | ✅ add .test |
| `hooks/__tests__/useUserActivityTimeout.ts` | `tests/hooks/useUserActivityTimeout.test.ts` | ✅ add .test |
| `hooks/__tests__/useVulnScanData.ts` | `tests/hooks/useVulnScanData.test.ts` | ✅ add .test |
| `pages/LoginGovCallback/__tests__/loginGovCallback.spec.tsx` | `tests/pages/LoginGovCallback/loginGovCallback.test.tsx` | ✅ spec→test |

### Step 3: RESTRUCTURE - Mirror Component Architecture

**REVISED APPROACH:** Instead of flattening all tests, mirror the actual component/page structure:

**Page Tests (incorrectly placed in components/):**
- `components/__tests__/domainDetails.spec.tsx` → `tests/pages/Domain/domainDetails.test.tsx`
- `components/__tests__/domainsTable.spec.tsx` → `tests/pages/Domains/domainsTable.test.tsx`  
- `components/__tests__/vulnerabilitiesTable.spec.tsx` → `tests/pages/Vulnerabilities/vulnerabilitiesTable.test.tsx`

**Component Tests (organized by actual component location):**
- `components/__tests__/header.spec.tsx` → `tests/components/Header/header.test.tsx`
- `components/__tests__/layout.spec.tsx` → `tests/components/layout.test.tsx` (root level)
- `components/__tests__/govBanner.spec.tsx` → `tests/components/govBanner.test.tsx` (root level)
- `components/__tests__/routeGuard.spec.tsx` → `tests/components/Routes/routeGuard.test.tsx`
- `components/__tests__/updateUserStateForm.spec.tsx` → `tests/components/UpdateUserStateForm/updateUserStateForm.test.tsx`
- `Dialog/TermsOfUse/__tests__/termsOfUse.spec.tsx` → `tests/components/Dialog/TermsOfUse/termsOfUse.test.tsx`
- `Gates/__tests__/vs-dashboard-gate.spec.tsx` → `tests/components/Gates/vs-dashboard-gate.test.tsx`

### Step 4: Import Path Updates

Update all import statements to use simple relative paths:
- From nested: `'../../components/Header/Header'` 
- To simple: `'../Header'` (when in same directory structure)

### Step 5: Snapshot Files Migration

Move snapshots to match the new structure:
- Create `__snapshots__` directories in appropriate test subdirectories
- Update snapshot file names to match new test file names (spec→test)

### Step 6: Configuration Updates

Check and update any test configuration files that might reference the old test locations:
- `vite.config.mts`
- `package.json` test scripts
- CI/CD configuration files

### Step 7: Fix Jest Remnants (Complete Vitest Migration) ✅ COMPLETED

**Issue Found:** Some hook tests still use Jest APIs instead of Vitest equivalents.

**Files to Fix:**
- `hooks/__tests__/usePersistentState.tsx`:
  - `jest.spyOn()` → `vi.spyOn()`
  - `jest.mocked()` → `vi.mocked()`
  - `jest.restoreAllMocks()` → `vi.restoreAllMocks()`
  - `jest.fn()` → `vi.fn()`
  
- `hooks/__tests__/useUserActivityTimeout.ts`:
  - `jest.useFakeTimers()` → `vi.useFakeTimers()`
  - `jest.clearAllTimers()` → `vi.clearAllTimers()`
  - `jest.advanceTimersByTime()` → `vi.advanceTimersByTime()`
  - Remove `jest-date-mock` import (not in package.json, likely causing errors)
  - Replace with Vitest date mocking alternatives

**Why This Matters:**
- Ensures complete consistency across all test files
- Eliminates dependency on Jest APIs
- Fixes potential runtime errors from missing `jest-date-mock`
- Completes the Jest → Vitest migration

## Current Status (After Initial Migration)

### ✅ Completed Steps:
1. **Created centralized tests directory** at `frontend/src/tests/`
2. **Moved and renamed all test files** from scattered `__tests__` directories
3. **Jest → Vitest conversion** completed for all hook tests
4. **Consistent naming**: All files now use `.test.tsx/.test.ts` convention
5. **Updated import paths** for all moved files
6. **All tests verified working** - 13/13 test files functional

### ⚠️ Current Issue: 
**Flattened structure doesn't match component organization**. Tests are currently in `tests/components/` root level but should mirror actual component structure.

### 🔄 Next: Restructure to Mirror Component Architecture

**Required Moves:**
- **Page tests** (incorrectly in components/) → `tests/pages/`
- **Nested components** → proper subdirectories matching `src/components/`
- **Update import paths** to use simple relative paths
- **Move snapshots** to appropriate subdirectories

## Acceptance Criteria Checklist

- [x] Create new folder: `frontend/src/tests/` 
- [x] All test files follow the `nameOfTest.test.tsx` naming convention
- [x] Update imports in test files and ensure tests still run
- [x] Complete Jest → Vitest migration
- [ ] **Mirror component/page directory structure in tests**
- [ ] No frontend unit tests are outside of the centralized tests folder
- [ ] Create subfolders within tests matching actual frontend code organization  
- [ ] All tests verified working after restructure
- [ ] Ensure CI and coverage still work

## Testing Types Reference

### Unit Test
Tests one small piece of code like a single function or component in isolation.

**Examples:**
- Testing the response of a function that fetches vulnerabilities
- Testing the return value of a function that converts UTC timestamp to human readable date
- Testing the resulting UI of a component that should render particular text

**Expectation:** Write unit tests with vitest for every frontend ticket that creates or updates a function or component.

### Functional (Integration) Test
Tests how multiple units work together to perform a specific function or feature.

**Examples:**
- Testing the resulting UI of a table by using the function that creates a loading state, using the function that fetches vulnerabilities, which then renders the table

**Expectation:** Write functional tests with vitest for every frontend ticket involving creating or updating a series of functions or components.

### E2E (End-to-end) Test
Tests that simulate a real user's experience from start to finish through the entire system.

**Examples:**
- Opens a browser, checks that a browser can open the app, enable the login command, confirms that the dashboard UI loads, and confirms a click to the "View Details" button goes to the vulnerabilities table

**Expectation:** Create an additional ticket to write an end-to-end test with playwright and a TODO inside the code with its CRASM number for every frontend ticket involving updating or creating several user-led actions in the frontend.

## Rollback Plan

If issues arise during migration:
1. All original files will be preserved until migration is confirmed successful
2. Git can be used to revert changes if needed
3. Original test locations are documented above for reference

## Post-Migration Verification

1. Run full test suite: `npm test`
2. Check test coverage reports
3. Verify CI pipeline passes
4. Confirm all imports resolve correctly
5. Validate snapshot tests still work

---

**Note:** This document should be kept updated throughout the migration process and can serve as a reference for future test organization standards.
