# XFD Testing Documentation Overview

Central hub for all testing-related documentation in the XFD (CyHy Dashboard) project.

## 📚 Documentation Index

### 🖥️ Frontend Testing
- **[Frontend Testing README](../frontend/src/tests/README.md)** - Main testing guide for frontend development
- **[CI Coverage & Reporting Guidelines](./frontend/CI_COVERAGE_GUIDELINES.md)** - Coverage thresholds, CI integration, and quality gates
- **[Unit Test Templates](./frontend/unit-templates/README.md)** - Ready-to-use test boilerplate
  - [Component Templates](./frontend/unit-templates/component-templates.md) - React component testing patterns
  - [Hook Templates](./frontend/unit-templates/hook-templates.md) - Custom React hook testing patterns  
  - [Utility Templates](./frontend/unit-templates/utility-templates.md) - Utility function testing patterns
  - [Context Templates](./frontend/unit-templates/context-templates.md) - React Context testing patterns
  - [Integration Templates](./frontend/unit-templates/integration-templates.md) - Multi-component testing patterns

### � Backend Testing
- **Backend Testing Documentation** - _Coming Soon_ 
- **Backend Test Templates** - _Coming Soon_

## �🚀 Quick Start

### For Frontend Developers
1. **Read**: [Frontend Testing README](../frontend/src/tests/README.md) - Start here for comprehensive overview
2. **Use**: [Unit Test Templates](./frontend/unit-templates/README.md) - Copy boilerplate for your tests
3. **Understand**: [CI Coverage Guidelines](./frontend/CI_COVERAGE_GUIDELINES.md) - Know the coverage requirements

### For Team Leads & DevOps
1. **Configure**: [CI Coverage Guidelines](./frontend/CI_COVERAGE_GUIDELINES.md) - Quality gates and thresholds
2. **Monitor**: Coverage reports and CI pipeline health

## 📊 Frontend Testing Stats

- **132+ test files** across the frontend codebase
- **~46% line coverage** with auto-updating thresholds
- **5 template categories** with 30+ individual templates  
- **Vitest + React Testing Library** as the core testing stack
- **GitHub Actions + Coveralls** for CI/CD integration

## 🎯 Frontend Testing Standards

### Coverage Requirements
- **Lines**: 46.5%+ (auto-updated)
- **Statements**: 46.0%+ (auto-updated)  
- **Functions**: 41.5%+ (auto-updated)
- **Branches**: 34.6%+ (auto-updated)

### Quality Gates
- All PRs must pass coverage thresholds
- New features require corresponding tests
- Tests must use consistent import patterns
- Coverage reports uploaded to Coveralls

### Best Practices
- Use test-utils for consistent provider setup
- Follow mirrored directory structure  
- Test user behavior, not implementation
- Include error scenarios and edge cases

## 🔗 Related Resources

### Internal Links
- [Contributing Guidelines](../src/documentation-pages/dev/guidelines.md)
- [Main Project Documentation](https://docs.crossfeed.cyber.dhs.gov)

### External Resources
- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Coveralls Dashboard](https://coveralls.io/github/cisagov/XFD)

## 📝 Document Maintenance

| Document | Owner | Review Cycle |
|----------|-------|--------------|
| Frontend Testing README | Solutions Team | Monthly |
| CI Coverage Guidelines | DevOps + Solutions Team | Quarterly |
| Unit Test Templates | Solutions Team | As needed |

---

**Last Updated**: February 25, 2026  
**Maintained By**: XFD Solutions Team
**Maintained By**: XFD Solutions Team
