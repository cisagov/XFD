# CI Coverage & Reporting Guidelines

**Document Purpose**: Define coverage thresholds, reporting formats, and CI behaviors for the XFD (CyHy Dashboard) frontend testing pipeline to ensure consistent quality gates and visibility.

**Target Audience**: Solutions team members, developers, and DevOps engineers working on the XFD project.

## Table of Contents

- [Overview](#overview)
- [Coverage Thresholds](#coverage-thresholds)
- [Local Development Commands](#local-development-commands)
- [CI Pipeline Integration](#ci-pipeline-integration)
- [Coverage Reports](#coverage-reports)
- [Quality Gates](#quality-gates)
- [Troubleshooting](#troubleshooting)

## Overview

The XFD frontend uses **Vitest** with **Istanbul** coverage provider to generate comprehensive test coverage reports. Coverage is enforced both locally and in CI environments to maintain code quality standards.

### Key Components
- **Coverage Provider**: Istanbul (via Vitest)
- **Reporters**: Text, JSON, HTML, LCOV
- **External Service**: Coveralls for coverage tracking and history
- **CI Platform**: GitHub Actions
- **Auto-Update**: Thresholds automatically update in CI to prevent regression

## Coverage Thresholds

### Current Thresholds (Auto-Updated)

The following thresholds are **automatically maintained** by the CI system and represent the current baseline coverage levels:

```typescript
// vite.config.mts - Coverage Configuration
thresholds: {
  statements: 45.98,  // Statement coverage
  branches: 34.61,    // Branch coverage  
  functions: 41.54,   // Function coverage
  lines: 46.5,        // Line coverage
  autoUpdate: true    // Automatically updated in CI
}
```

> **📊 Threshold Behavior**: When `autoUpdate: true` is enabled in CI environments, these thresholds automatically increase if coverage improves, preventing regression while allowing organic improvement.

### Target Thresholds (Aspirational)

The project aims to achieve the following coverage levels over time:

| Metric | Current | Target | Priority |
|--------|---------|---------|----------|
| **Lines** | 46.5% | 80%+ | High |
| **Statements** | 45.98% | 80%+ | High |
| **Functions** | 41.54% | 75%+ | Medium |
| **Branches** | 34.61% | 70%+ | Medium |

### Included in Coverage

Coverage analysis includes the following directories:
- `src/components/**/*.{js,ts,jsx,tsx}`
- `src/context/**/*.{js,ts,jsx,tsx}`
- `src/hooks/**/*.{js,ts,jsx,tsx}`
- `src/pages/**/*.{js,ts,jsx,tsx}`
- `src/utils/**/*.{js,ts,jsx,tsx}`

### Excluded from Coverage

The following files/directories are excluded from coverage analysis:
- `src/setupTests.ts` - Test configuration
- `src/utils/openInVSCode.ts` - Development utility
- `src/utils/devInspector.tsx` - Development utility  
- `src/**/types.*` - Type definitions
- `src/**/index.{js,ts,tsx}` - Export files
- `src/**/*[Ss]tyle*` - Style-related files
- `src/components/MatomoTracker/*` - Analytics tracking
- `src/components/Metrics/*` - Metrics components

## Local Development Commands

### Basic Coverage Commands

```bash
# Generate coverage report (recommended for development)
npm run test:coverage

# Alternative: Run tests with coverage directly
npx vitest run --coverage

# Watch mode with coverage (updates as files change)
npx vitest --watch --coverage

# Coverage for specific files/patterns
npx vitest run --coverage src/components/Header/
npx vitest run --coverage --reporter=verbose
```

### Viewing Coverage Reports

```bash
# Generate and open HTML coverage report
npm run test:coverage && open coverage/index.html

# macOS: Open in default browser
open ./coverage/index.html

# Linux: Open in default browser  
xdg-open ./coverage/index.html

# Windows: Open in default browser
start ./coverage/index.html
```

### Coverage Analysis Commands

```bash
# Generate coverage with detailed output
npx vitest run --coverage --reporter=verbose

# Coverage with specific thresholds (override config)
npx vitest run --coverage --coverage.statements=50 --coverage.branches=40

# Coverage excluding specific patterns
npx vitest run --coverage --exclude="**/test-utils/**"

# Generate only specific report formats
npx vitest run --coverage --coverage.reporter=html,text
```

## CI Pipeline Integration

### GitHub Actions Workflow

The frontend CI pipeline (`.github/workflows/frontend.yml`) includes the following coverage steps:

```yaml
- name: Run tests with coverage
  run: CI=true npx vitest --run --coverage
  working-directory: ./frontend

- name: Upload coverage to Coveralls
  uses: coverallsapp/github-action@v2
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    path-to-lcov: ./frontend/coverage/lcov.info
```

### Environment Variables

| Variable | Purpose | Value |
|----------|---------|-------|
| `CI=true` | Enables CI mode in Vitest | `true` |
| `isCI` | Controls threshold auto-update | `process.env.CI === 'true'` |

### CI Behavior

1. **Test Execution**: Tests run in non-interactive mode (`--run`) with coverage
2. **Threshold Enforcement**: Coverage must meet or exceed current thresholds
3. **Auto-Update**: If coverage improves, thresholds automatically update
4. **Report Upload**: LCOV report uploaded to Coveralls for tracking
5. **Failure Handling**: Build fails if coverage drops below thresholds

## Coverage Reports

### Report Formats Generated

| Format | File Location | Purpose |
|--------|---------------|---------|
| **HTML** | `./coverage/index.html` | Interactive browser-based report |
| **LCOV** | `./coverage/lcov.info` | Machine-readable for CI/external tools |
| **JSON** | `./coverage/coverage-final.json` | Programmatic access to coverage data |
| **Text** | Console output | Quick overview during test runs |

### HTML Report Features

The HTML coverage report (`./coverage/index.html`) provides:

- 📊 **Overall Coverage Summary**: All metrics at a glance
- 📁 **Directory-by-Directory Breakdown**: Coverage by folder structure  
- 📄 **File-Level Detail**: Line-by-line coverage visualization
- 🎨 **Color-Coded Lines**: Green (covered), red (uncovered), yellow (partial)
- 🔍 **Interactive Navigation**: Click through to explore uncovered areas
- 📈 **Historical Context**: When integrated with external services

### Coveralls Integration

**Coveralls URL**: [https://coveralls.io/github/cisagov/XFD](https://coveralls.io/github/cisagov/XFD)

Coveralls provides:
- Coverage history and trends
- Pull request coverage changes
- Comparison between branches
- Coverage badges for README
- Team notifications

## Quality Gates

### Pull Request Requirements

All pull requests must:
- ✅ **Pass Coverage Thresholds**: Meet or exceed current threshold levels
- ✅ **Include Tests for New Code**: New features require corresponding tests
- ✅ **Not Regress Coverage**: Cannot decrease overall coverage percentage
- ✅ **Generate Valid Reports**: All report formats must generate successfully

### Deployment Gates

| Environment | Coverage Requirement | Additional Checks |
|-------------|---------------------|-------------------|
| **Staging** | Must pass all thresholds | Lint + Build success |
| **Integration** | Must pass all thresholds | Lint + Build success |
| **Production** | Must pass all thresholds | Full test suite + Manual approval |

### Failure Scenarios

The CI pipeline will **FAIL** if:
- Coverage drops below any configured threshold
- LCOV report generation fails
- Coverage upload to Coveralls fails
- Test execution encounters errors

## Troubleshooting

### Common Coverage Issues

#### ❌ "Coverage threshold not met"
```bash
Error: Coverage threshold for lines (46.5%) not met. Actual: 45.2%
```

**Solutions**:
1. Add tests for uncovered lines
2. Remove dead/unreachable code
3. Review if thresholds need adjustment (discuss with team)

#### ❌ "Istanbul coverage provider failed"
```bash
Error: Coverage provider 'istanbul' failed to generate report
```

**Solutions**:
```bash
# Clear coverage cache
rm -rf coverage/
rm -rf node_modules/.vite/

# Reinstall dependencies
npm ci

# Run coverage again
npm run test:coverage
```

#### ❌ "LCOV upload failed"
```bash
Error: Failed to upload coverage to Coveralls
```

**Solutions**:
1. Check GitHub token permissions
2. Verify repository is connected to Coveralls
3. Check LCOV file exists and is valid:
   ```bash
   ls -la ./coverage/lcov.info
   head -n 10 ./coverage/lcov.info
   ```

### Coverage Analysis Tips

#### Identifying Uncovered Code
```bash
# Generate detailed coverage with uncovered lines
npx vitest run --coverage --reporter=verbose

# Focus on specific directories
npx vitest run --coverage src/components/ --reporter=verbose
```

#### Understanding Coverage Gaps
1. **Open HTML Report**: Most effective for visual analysis
2. **Check Branch Coverage**: Often lower than line coverage
3. **Review Error Handling**: Error paths frequently uncovered
4. **Examine Edge Cases**: Conditional logic may need additional tests

#### Performance Considerations
```bash
# Skip coverage for faster test runs during development
npm test

# Only generate coverage when needed
npm run test:coverage
```

### Local Development Best Practices

1. **Pre-Commit**: Run coverage locally before pushing
2. **Incremental**: Check coverage for files you're modifying
3. **HTML Report**: Use interactive report to guide test writing
4. **Threshold Awareness**: Keep current thresholds in mind when making changes

### CI Debugging Commands

```bash
# Simulate CI environment locally
CI=true npx vitest --run --coverage

# Generate same reports as CI
npx vitest run --coverage --reporter=text,json,html,lcov

# Check LCOV format validity
npx lcov-parse ./coverage/lcov.info
```

## Integration with Developer Guidelines

This coverage configuration aligns with the XFD project's development standards:

- **Quality Assurance**: Maintains consistent testing standards across the codebase
- **Continuous Improvement**: Auto-updating thresholds encourage gradual improvement
- **Visibility**: Coveralls integration provides team-wide coverage awareness
- **Automation**: CI integration ensures coverage requirements are consistently enforced

For additional testing guidance, see:
- [Frontend Testing Documentation](../frontend/src/tests/README.md)
- [Unit Test Templates](./unit-templates/README.md)
- [Testing Audit Summary](./TESTING_AUDIT_SUMMARY.md)

---

**Last Updated**: February 23, 2026  
**Document Owner**: Solutions Team  
**Review Cycle**: Quarterly or after major coverage threshold changes
