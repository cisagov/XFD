# Frontend Unit Test Templates

This directory contains ready-to-use templates and examples for writing unit tests in the XFD (CyHy Dashboard) frontend application.

> **⚠️ Current State Notice**: The XFD codebase has mixed import patterns and testing approaches. These templates represent the **recommended patterns** for new tests, but existing tests may use different approaches. See the [main testing documentation](../../frontend/src/tests/README.md) for details about current inconsistencies and migration guidance.

## Templates Available

- [**Component Templates**](./component-templates.md) - Templates for testing React components
- [**Hook Templates**](./hook-templates.md) - Templates for testing custom React hooks  
- [**Utility Templates**](./utility-templates.md) - Templates for testing utility functions
- [**Context Templates**](./context-templates.md) - Templates for testing React Context providers
- [**Integration Templates**](./integration-templates.md) - Templates for integration tests

## Quick Start

1. **Choose the appropriate template** based on what you're testing
2. **Copy the template code** to your new test file
3. **Replace placeholder values** with your actual component/hook/utility names
4. **Customize test cases** for your specific functionality
5. **Follow the naming conventions** outlined in each template

## Template Structure

Each template includes:
- ✅ **Import statements** with correct paths and utilities
- ✅ **Mock setup** for common dependencies  
- ✅ **Describe blocks** with proper organization
- ✅ **Test cases** covering common scenarios
- ✅ **Best practices** and helpful comments
- ✅ **XFD-specific patterns** for authentication, Material-UI, etc.

## Getting Started

For your first test, we recommend starting with the [Component Templates](./component-templates.md) as they cover the most common testing scenarios in the XFD application.

## Need Help?

- Check the [main testing documentation](../../../../frontend/src/tests/README.md)
- Review existing tests in `frontend/src/tests/` for patterns
- See [CI Coverage & Reporting Guidelines](../CI_COVERAGE_GUIDELINES.md) for coverage requirements
- Consult the troubleshooting section in the main README

---

**Last Updated**: February 2026
