# Frontend Unit Test Templates

This directory contains generalized templates for writing unit tests in the XFD (CyHy Dashboard) frontend application.

## Available Templates

- [**Component Templates**](./component-templates.md) - General patterns for testing React components
- [**Hook Templates**](./hook-templates.md) - General patterns for testing custom React hooks  
- [**Utility Templates**](./utility-templates.md) - General patterns for testing utility functions
- [**Context Templates**](./context-templates.md) - General patterns for testing React Context providers

## Philosophy

These templates focus on **general testing patterns** rather than covering every edge case. They provide a solid foundation that you can adapt for your specific needs.

## Key Principles

- **Use test-utils**: Centralized repository of reusable testing artifacts (contexts, mocks, helpers)
- **General patterns**: Templates show common testing approaches, not exhaustive scenarios
- **Adaptable**: Copy and customize for your specific use case
- **Consistent imports**: Standardized patterns using `@` aliases and `test-utils`

## Template Structure

Each template includes:
- ✅ **Standard imports** from `test-utils`
- ✅ **Basic test structure** with describe blocks
- ✅ **Common test cases** (happy path, error handling)
- ✅ **XFD-specific setup** (auth context, theme providers)
- ✅ **Helpful comments** explaining key concepts

## Getting Started

1. **Choose the appropriate template** for your test type
2. **Copy the basic structure** to your test file
3. **Customize** for your specific component/hook/utility
4. **Add additional test cases** as needed for your functionality

For more detailed guidance, see the [main testing documentation](../../../../frontend/src/tests/README.md).

---

**Last Updated**: March 2026
