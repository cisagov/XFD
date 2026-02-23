# Utility Test Templates

Templates for testing utility functions in the XFD frontend application.

> **📝 Important Note**: The XFD codebase currently has mixed import patterns. These templates show the recommended patterns, but you may see existing tests using different import styles. For new tests, use the patterns shown in these templates.

## Table of Contents

- [Basic Utility Function Template](#basic-utility-function-template)
- [Pure Function with Multiple Inputs Template](#pure-function-with-multiple-inputs-template)
- [Date/Time Utility Template](#datetime-utility-template)
- [String Manipulation Utility Template](#string-manipulation-utility-template)
- [Data Transformation Utility Template](#data-transformation-utility-template)
- [Validation Utility Template](#validation-utility-template)
- [Utility with External Dependencies Template](#utility-with-external-dependencies-template)

---

## Basic Utility Function Template

Use this for simple pure functions with predictable inputs and outputs.

```typescript
import { describe, expect, it } from 'vitest';
import { yourUtilityFunction } from '../../utils/yourUtilityFunction';

describe('yourUtilityFunction', () => {
  it('returns expected result for valid input', () => {
    const input = 'test-input';
    const result = yourUtilityFunction(input);
    
    expect(result).toBe('expected-output');
  });

  it('handles empty input', () => {
    const result = yourUtilityFunction('');
    
    expect(result).toBe('default-value');
  });

  it('handles null and undefined inputs', () => {
    expect(yourUtilityFunction(null)).toBe(null);
    expect(yourUtilityFunction(undefined)).toBe(undefined);
  });

  it('handles different data types', () => {
    expect(yourUtilityFunction('string')).toBe('string-result');
    expect(yourUtilityFunction(123)).toBe('number-result');
    expect(yourUtilityFunction(true)).toBe('boolean-result');
  });

  it('is a pure function (same input produces same output)', () => {
    const input = 'consistent-input';
    const result1 = yourUtilityFunction(input);
    const result2 = yourUtilityFunction(input);
    
    expect(result1).toBe(result2);
  });

  it('does not mutate input parameters', () => {
    const originalInput = { value: 'original' };
    const inputCopy = { ...originalInput };
    
    yourUtilityFunction(originalInput);
    
    expect(originalInput).toEqual(inputCopy);
  });
});
```

---

## Pure Function with Multiple Inputs Template

Use this for functions that take multiple parameters and need comprehensive input testing.

```typescript
import { describe, expect, it } from 'vitest';
import { yourMultiParamFunction } from '../../utils/yourMultiParamFunction';

describe('yourMultiParamFunction', () => {
  it('works with all required parameters', () => {
    const result = yourMultiParamFunction('param1', 'param2', 'param3');
    
    expect(result).toBe('expected-result');
  });

  it('works with optional parameters', () => {
    // Test with optional parameter provided
    const withOptional = yourMultiParamFunction('param1', 'param2', 'param3', 'optional');
    expect(withOptional).toBe('result-with-optional');

    // Test without optional parameter
    const withoutOptional = yourMultiParamFunction('param1', 'param2', 'param3');
    expect(withoutOptional).toBe('result-without-optional');
  });

  it('handles parameter combinations correctly', () => {
    // Test various combinations
    const combinations = [
      { input: ['a', 'b', 'c'], expected: 'abc-result' },
      { input: ['x', 'y', 'z'], expected: 'xyz-result' },
      { input: ['1', '2', '3'], expected: '123-result' }
    ];

    combinations.forEach(({ input, expected }) => {
      const result = yourMultiParamFunction(...input);
      expect(result).toBe(expected);
    });
  });

  it('validates parameter types', () => {
    expect(() => {
      yourMultiParamFunction(null, 'param2', 'param3');
    }).toThrow('Invalid parameter type');

    expect(() => {
      yourMultiParamFunction('param1', undefined, 'param3');
    }).toThrow('Parameter cannot be undefined');
  });

  it('handles edge cases', () => {
    // Empty strings
    const emptyResult = yourMultiParamFunction('', '', '');
    expect(emptyResult).toBe('empty-result');

    // Very long strings
    const longString = 'a'.repeat(1000);
    const longResult = yourMultiParamFunction(longString, 'param2', 'param3');
    expect(typeof longResult).toBe('string');

    // Special characters
    const specialResult = yourMultiParamFunction('!@#', '$%^', '&*()');
    expect(specialResult).toBeDefined();
  });

  it('maintains function purity with complex objects', () => {
    const obj1 = { nested: { value: 1 } };
    const obj2 = { nested: { value: 2 } };
    const obj3 = { nested: { value: 3 } };
    
    const original1 = JSON.stringify(obj1);
    const original2 = JSON.stringify(obj2);
    const original3 = JSON.stringify(obj3);
    
    yourMultiParamFunction(obj1, obj2, obj3);
    
    expect(JSON.stringify(obj1)).toBe(original1);
    expect(JSON.stringify(obj2)).toBe(original2);
    expect(JSON.stringify(obj3)).toBe(original3);
  });

  it('handles default parameter values', () => {
    const resultWithDefaults = yourMultiParamFunction();
    expect(resultWithDefaults).toBe('default-result');
    
    const resultWithSomeDefaults = yourMultiParamFunction('custom');
    expect(resultWithSomeDefaults).toBe('custom-default-result');
  });
});
```

---

## Date/Time Utility Template

Use this for functions that work with dates, times, and temporal calculations.

```typescript
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import {
  formatDate,
  isDateWithinRange,
  calculateTimeDifference
} from '../../utils/dateUtils';

describe('Date/Time Utilities', () => {
  beforeEach(() => {
    // Mock current date for consistent testing
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-02-19T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('formatDate', () => {
    it('formats date strings correctly', () => {
      const dateString = '2026-02-19T12:00:00Z';
      const result = formatDate(dateString, 'MM/dd/yyyy');
      
      expect(result).toBe('02/19/2026');
    });

    it('formats Date objects correctly', () => {
      const date = new Date('2026-02-19T12:00:00Z');
      const result = formatDate(date, 'yyyy-MM-dd');
      
      expect(result).toBe('2026-02-19');
    });

    it('handles different format patterns', () => {
      const date = '2026-02-19T15:30:45Z';
      
      expect(formatDate(date, 'MM/dd/yyyy')).toBe('02/19/2026');
      expect(formatDate(date, 'dd-MM-yyyy')).toBe('19-02-2026');
      expect(formatDate(date, 'yyyy-MM-dd HH:mm')).toBe('2026-02-19 15:30');
    });

    it('handles invalid dates gracefully', () => {
      expect(formatDate('invalid-date')).toBe('Invalid Date');
      expect(formatDate(null)).toBe('');
      expect(formatDate(undefined)).toBe('');
    });

    it('handles timezone conversions', () => {
      const utcDate = '2026-02-19T12:00:00Z';
      const estResult = formatDate(utcDate, 'yyyy-MM-dd HH:mm', 'America/New_York');
      
      expect(estResult).toMatch(/2026-02-19 (07|08):00/); // Handles DST
    });
  });

  describe('isDateWithinRange', () => {
    it('returns true for dates within range', () => {
      const testDate = new Date('2026-02-19T12:00:00Z');
      const startDate = new Date('2026-02-18T12:00:00Z');
      const endDate = new Date('2026-02-20T12:00:00Z');
      
      const result = isDateWithinRange(testDate, startDate, endDate);
      
      expect(result).toBe(true);
    });

    it('returns false for dates outside range', () => {
      const testDate = new Date('2026-02-21T12:00:00Z');
      const startDate = new Date('2026-02-18T12:00:00Z');
      const endDate = new Date('2026-02-20T12:00:00Z');
      
      const result = isDateWithinRange(testDate, startDate, endDate);
      
      expect(result).toBe(false);
    });

    it('handles boundary dates correctly', () => {
      const startDate = new Date('2026-02-19T12:00:00Z');
      const endDate = new Date('2026-02-19T12:00:00Z');
      
      // Test exact start date
      expect(isDateWithinRange(startDate, startDate, endDate)).toBe(true);
      
      // Test exact end date
      expect(isDateWithinRange(endDate, startDate, endDate)).toBe(true);
    });

    it('handles string date inputs', () => {
      const result = isDateWithinRange(
        '2026-02-19',
        '2026-02-18',
        '2026-02-20'
      );
      
      expect(result).toBe(true);
    });
  });

  describe('calculateTimeDifference', () => {
    it('calculates difference in days correctly', () => {
      const date1 = new Date('2026-02-19T12:00:00Z');
      const date2 = new Date('2026-02-21T12:00:00Z');
      
      const result = calculateTimeDifference(date1, date2, 'days');
      
      expect(result).toBe(2);
    });

    it('calculates difference in hours correctly', () => {
      const date1 = new Date('2026-02-19T12:00:00Z');
      const date2 = new Date('2026-02-19T15:00:00Z');
      
      const result = calculateTimeDifference(date1, date2, 'hours');
      
      expect(result).toBe(3);
    });

    it('handles negative differences', () => {
      const date1 = new Date('2026-02-21T12:00:00Z');
      const date2 = new Date('2026-02-19T12:00:00Z');
      
      const result = calculateTimeDifference(date1, date2, 'days');
      
      expect(result).toBe(-2);
    });

    it('handles same dates', () => {
      const date = new Date('2026-02-19T12:00:00Z');
      
      const result = calculateTimeDifference(date, date, 'days');
      
      expect(result).toBe(0);
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('handles leap year calculations', () => {
      const leapYearDate = new Date('2024-02-29T12:00:00Z'); // Leap year
      const result = formatDate(leapYearDate, 'yyyy-MM-dd');
      
      expect(result).toBe('2024-02-29');
    });

    it('handles different time zones', () => {
      const utcDate = new Date('2026-02-19T23:30:00Z');
      
      // Should handle timezone differences without throwing
      expect(() => formatDate(utcDate, 'yyyy-MM-dd HH:mm')).not.toThrow();
    });

    it('handles daylight saving time transitions', () => {
      // Test dates around DST transition
      const beforeDST = new Date('2026-03-07T12:00:00Z'); // Before DST
      const afterDST = new Date('2026-03-15T12:00:00Z');  // After DST
      
      expect(() => {
        calculateTimeDifference(beforeDST, afterDST, 'days');
      }).not.toThrow();
    });
  });
});
```

---

## String Manipulation Utility Template

Use this for functions that manipulate, validate, or transform strings.

```typescript
import { describe, expect, it } from 'vitest';
import {
  sanitizeString,
  truncateString,
  capitalizeWords,
  extractEmails,
  generateSlug
} from '../../utils/stringUtils';

describe('String Manipulation Utilities', () => {
  describe('sanitizeString', () => {
    it('removes harmful HTML tags', () => {
      const maliciousInput = '<script>alert("xss")</script>Hello World';
      const result = sanitizeString(maliciousInput);
      
      expect(result).toBe('Hello World');
      expect(result).not.toContain('<script>');
    });

    it('preserves safe HTML tags when allowed', () => {
      const input = '<p>Hello <strong>World</strong></p>';
      const result = sanitizeString(input, { allowedTags: ['p', 'strong'] });
      
      expect(result).toBe('<p>Hello <strong>World</strong></p>');
    });

    it('handles special characters correctly', () => {
      const input = 'Price: $10.99 & change < 5%';
      const result = sanitizeString(input);
      
      expect(result).toContain('$10.99');
      expect(result).toContain('&');
      expect(result).toContain('< 5%');
    });

    it('handles empty and null inputs', () => {
      expect(sanitizeString('')).toBe('');
      expect(sanitizeString(null)).toBe('');
      expect(sanitizeString(undefined)).toBe('');
    });
  });

  describe('truncateString', () => {
    it('truncates long strings correctly', () => {
      const longString = 'This is a very long string that should be truncated';
      const result = truncateString(longString, 20);
      
      expect(result).toBe('This is a very long...');
      expect(result.length).toBe(23); // 20 + 3 for '...'
    });

    it('returns original string if shorter than limit', () => {
      const shortString = 'Short';
      const result = truncateString(shortString, 20);
      
      expect(result).toBe('Short');
    });

    it('handles custom ellipsis', () => {
      const string = 'This is a test string';
      const result = truncateString(string, 10, ' [more]');
      
      expect(result).toBe('This is a [more]');
    });

    it('handles word boundary truncation', () => {
      const string = 'This is a test string';
      const result = truncateString(string, 12, '...', true); // Respect word boundaries
      
      expect(result).toBe('This is a...');
    });

    it('handles edge cases', () => {
      expect(truncateString('', 10)).toBe('');
      expect(truncateString('Test', 0)).toBe('...');
      expect(truncateString(null, 10)).toBe('');
    });
  });

  describe('capitalizeWords', () => {
    it('capitalizes first letter of each word', () => {
      const input = 'hello world test';
      const result = capitalizeWords(input);
      
      expect(result).toBe('Hello World Test');
    });

    it('handles mixed case input', () => {
      const input = 'hELLo WoRLd';
      const result = capitalizeWords(input);
      
      expect(result).toBe('Hello World');
    });

    it('handles special characters and numbers', () => {
      const input = 'test-123 hello_world';
      const result = capitalizeWords(input);
      
      expect(result).toBe('Test-123 Hello_world');
    });

    it('preserves multiple spaces', () => {
      const input = 'hello    world';
      const result = capitalizeWords(input);
      
      expect(result).toBe('Hello    World');
    });

    it('handles empty and null inputs', () => {
      expect(capitalizeWords('')).toBe('');
      expect(capitalizeWords(null)).toBe('');
      expect(capitalizeWords(undefined)).toBe('');
    });
  });

  describe('extractEmails', () => {
    it('extracts valid email addresses', () => {
      const text = 'Contact us at test@example.com or support@company.org';
      const result = extractEmails(text);
      
      expect(result).toEqual(['test@example.com', 'support@company.org']);
    });

    it('handles various email formats', () => {
      const text = 'Emails: user.name@domain.com, test+tag@example.co.uk';
      const result = extractEmails(text);
      
      expect(result).toContain('user.name@domain.com');
      expect(result).toContain('test+tag@example.co.uk');
    });

    it('ignores invalid email formats', () => {
      const text = 'Invalid: @example.com, test@, incomplete@domain';
      const result = extractEmails(text);
      
      expect(result).toEqual([]); // Should not match invalid formats
    });

    it('removes duplicate emails', () => {
      const text = 'Same email: test@example.com and test@example.com again';
      const result = extractEmails(text);
      
      expect(result).toEqual(['test@example.com']);
    });

    it('handles empty input', () => {
      expect(extractEmails('')).toEqual([]);
      expect(extractEmails(null)).toEqual([]);
    });
  });

  describe('generateSlug', () => {
    it('converts string to URL-friendly slug', () => {
      const input = 'Hello World Test';
      const result = generateSlug(input);
      
      expect(result).toBe('hello-world-test');
    });

    it('handles special characters', () => {
      const input = 'Test & Example: Special Characters!';
      const result = generateSlug(input);
      
      expect(result).toBe('test-example-special-characters');
    });

    it('handles multiple spaces and dashes', () => {
      const input = 'Multiple    Spaces---And   Dashes';
      const result = generateSlug(input);
      
      expect(result).toBe('multiple-spaces-and-dashes');
    });

    it('handles Unicode characters', () => {
      const input = 'Café & Résumé';
      const result = generateSlug(input);
      
      expect(result).toBe('cafe-resume');
    });

    it('handles numbers correctly', () => {
      const input = 'Version 2.0 Beta 3';
      const result = generateSlug(input);
      
      expect(result).toBe('version-20-beta-3');
    });

    it('handles edge cases', () => {
      expect(generateSlug('')).toBe('');
      expect(generateSlug('   ')).toBe('');
      expect(generateSlug('!!!')).toBe('');
      expect(generateSlug(null)).toBe('');
    });
  });
});
```

---

## Data Transformation Utility Template

Use this for functions that transform, filter, or manipulate data structures.

```typescript
import { describe, expect, it } from 'vitest';
import {
  transformTableData,
  filterByProperty,
  groupByProperty,
  sortByProperty,
  flattenNestedData
} from '../../utils/dataTransformUtils';

// Mock data for testing
const mockTableData = [
  { id: 1, name: 'Alice', department: 'Engineering', salary: 75000, active: true },
  { id: 2, name: 'Bob', department: 'Marketing', salary: 65000, active: false },
  { id: 3, name: 'Charlie', department: 'Engineering', salary: 80000, active: true },
  { id: 4, name: 'Diana', department: 'Sales', salary: 70000, active: true }
];

const mockNestedData = [
  {
    id: 1,
    user: { name: 'Alice', profile: { age: 30, location: 'NYC' } },
    skills: ['JavaScript', 'React']
  },
  {
    id: 2,
    user: { name: 'Bob', profile: { age: 25, location: 'LA' } },
    skills: ['Python', 'Django']
  }
];

describe('Data Transformation Utilities', () => {
  describe('transformTableData', () => {
    it('transforms data to display format', () => {
      const result = transformTableData(mockTableData, {
        columns: ['name', 'department', 'salary'],
        formatters: {
          salary: (value: number) => `$${value.toLocaleString()}`
        }
      });
      
      expect(result).toHaveLength(4);
      expect(result[0].salary).toBe('$75,000');
      expect(result[0]).toHaveProperty('name', 'Alice');
    });

    it('handles column selection', () => {
      const result = transformTableData(mockTableData, {
        columns: ['name', 'salary']
      });
      
      expect(result[0]).toHaveProperty('name');
      expect(result[0]).toHaveProperty('salary');
      expect(result[0]).not.toHaveProperty('department');
    });

    it('handles custom column mappings', () => {
      const result = transformTableData(mockTableData, {
        columnMappings: {
          name: 'Employee Name',
          department: 'Dept',
          salary: 'Annual Salary'
        }
      });
      
      expect(result[0]).toHaveProperty('Employee Name', 'Alice');
      expect(result[0]).toHaveProperty('Dept', 'Engineering');
    });

    it('handles empty data gracefully', () => {
      const result = transformTableData([], { columns: ['name'] });
      
      expect(result).toEqual([]);
    });

    it('handles invalid data', () => {
      expect(() => transformTableData(null, {})).not.toThrow();
      expect(transformTableData(null, {})).toEqual([]);
    });
  });

  describe('filterByProperty', () => {
    it('filters by single property value', () => {
      const result = filterByProperty(mockTableData, 'department', 'Engineering');
      
      expect(result).toHaveLength(2);
      expect(result.every(item => item.department === 'Engineering')).toBe(true);
    });

    it('filters by multiple values', () => {
      const result = filterByProperty(mockTableData, 'department', ['Engineering', 'Sales']);
      
      expect(result).toHaveLength(3);
      expect(result.every(item => 
        item.department === 'Engineering' || item.department === 'Sales'
      )).toBe(true);
    });

    it('filters by boolean property', () => {
      const result = filterByProperty(mockTableData, 'active', true);
      
      expect(result).toHaveLength(3);
      expect(result.every(item => item.active === true)).toBe(true);
    });

    it('handles custom filter functions', () => {
      const result = filterByProperty(
        mockTableData, 
        'salary', 
        (salary: number) => salary > 70000
      );
      
      expect(result).toHaveLength(2);
      expect(result.every(item => item.salary > 70000)).toBe(true);
    });

    it('handles non-existent properties', () => {
      const result = filterByProperty(mockTableData, 'nonExistent', 'value');
      
      expect(result).toHaveLength(0);
    });
  });

  describe('groupByProperty', () => {
    it('groups data by single property', () => {
      const result = groupByProperty(mockTableData, 'department');
      
      expect(result).toHaveProperty('Engineering');
      expect(result).toHaveProperty('Marketing');
      expect(result).toHaveProperty('Sales');
      expect(result.Engineering).toHaveLength(2);
      expect(result.Marketing).toHaveLength(1);
    });

    it('groups by nested property', () => {
      const nestedData = [
        { id: 1, user: { department: 'Engineering' }, value: 10 },
        { id: 2, user: { department: 'Engineering' }, value: 20 },
        { id: 3, user: { department: 'Marketing' }, value: 15 }
      ];
      
      const result = groupByProperty(nestedData, 'user.department');
      
      expect(result.Engineering).toHaveLength(2);
      expect(result.Marketing).toHaveLength(1);
    });

    it('handles custom grouping functions', () => {
      const result = groupByProperty(
        mockTableData,
        (item) => item.salary > 70000 ? 'high' : 'low'
      );
      
      expect(result).toHaveProperty('high');
      expect(result).toHaveProperty('low');
      expect(result.high).toHaveLength(2);
      expect(result.low).toHaveLength(2);
    });

    it('handles empty data', () => {
      const result = groupByProperty([], 'property');
      
      expect(result).toEqual({});
    });
  });

  describe('sortByProperty', () => {
    it('sorts by string property ascending', () => {
      const result = sortByProperty(mockTableData, 'name', 'asc');
      
      expect(result[0].name).toBe('Alice');
      expect(result[3].name).toBe('Diana');
    });

    it('sorts by string property descending', () => {
      const result = sortByProperty(mockTableData, 'name', 'desc');
      
      expect(result[0].name).toBe('Diana');
      expect(result[3].name).toBe('Alice');
    });

    it('sorts by number property', () => {
      const result = sortByProperty(mockTableData, 'salary', 'desc');
      
      expect(result[0].salary).toBe(80000);
      expect(result[3].salary).toBe(65000);
    });

    it('sorts by multiple properties', () => {
      const result = sortByProperty(
        mockTableData, 
        ['department', 'salary'], 
        ['asc', 'desc']
      );
      
      // Engineering entries should come first, with higher salaries first
      expect(result[0].department).toBe('Engineering');
      expect(result[0].salary).toBe(80000);
      expect(result[1].department).toBe('Engineering');
      expect(result[1].salary).toBe(75000);
    });

    it('handles custom sort functions', () => {
      const result = sortByProperty(
        mockTableData,
        (a, b) => a.name.length - b.name.length
      );
      
      expect(result[0].name).toBe('Bob'); // Shortest name
      expect(result[3].name).toBe('Charlie'); // Longest name
    });

    it('maintains stable sort', () => {
      const duplicateData = [
        ...mockTableData,
        { id: 5, name: 'Alice', department: 'HR', salary: 75000, active: true }
      ];
      
      const result = sortByProperty(duplicateData, 'name', 'asc');
      
      // Original Alice should come before new Alice (stable sort)
      expect(result[0].id).toBe(1);
      expect(result[1].id).toBe(5);
    });
  });

  describe('flattenNestedData', () => {
    it('flattens nested object properties', () => {
      const result = flattenNestedData(mockNestedData);
      
      expect(result[0]).toHaveProperty('user.name', 'Alice');
      expect(result[0]).toHaveProperty('user.profile.age', 30);
      expect(result[0]).toHaveProperty('user.profile.location', 'NYC');
    });

    it('handles arrays in nested data', () => {
      const result = flattenNestedData(mockNestedData);
      
      expect(result[0]).toHaveProperty('skills.0', 'JavaScript');
      expect(result[0]).toHaveProperty('skills.1', 'React');
    });

    it('handles custom separator', () => {
      const result = flattenNestedData(mockNestedData, '_');
      
      expect(result[0]).toHaveProperty('user_name', 'Alice');
      expect(result[0]).toHaveProperty('user_profile_age', 30);
    });

    it('handles maximum depth', () => {
      const result = flattenNestedData(mockNestedData, '.', 2);
      
      expect(result[0]).toHaveProperty('user.name');
      expect(result[0]).toHaveProperty('user.profile');
      expect(result[0]).not.toHaveProperty('user.profile.age');
    });

    it('handles primitive values', () => {
      const primitiveData = [{ id: 1, name: 'test', active: true }];
      const result = flattenNestedData(primitiveData);
      
      expect(result[0]).toEqual({ id: 1, name: 'test', active: true });
    });

    it('handles empty and null values', () => {
      const dataWithNulls = [
        { id: 1, user: null, profile: { name: 'test' } },
        { id: 2, user: { name: 'Alice' }, profile: undefined }
      ];
      
      const result = flattenNestedData(dataWithNulls);
      
      expect(result[0]).toHaveProperty('user', null);
      expect(result[0]).toHaveProperty('profile.name', 'test');
      expect(result[1]).toHaveProperty('user.name', 'Alice');
    });
  });
});
```

---

## Validation Utility Template

Use this for functions that validate data, forms, or user inputs.

```typescript
import { describe, expect, it } from 'vitest';
import {
  validateEmail,
  validatePassword,
  validatePhoneNumber,
  validateURL,
  validateFormData,
  isValidJSON
} from '../../utils/validationUtils';

describe('Validation Utilities', () => {
  describe('validateEmail', () => {
    it('validates correct email addresses', () => {
      const validEmails = [
        'test@example.com',
        'user.name@domain.co.uk',
        'user+tag@example.org',
        'firstname.lastname@company.com.au'
      ];
      
      validEmails.forEach(email => {
        expect(validateEmail(email)).toBe(true);
      });
    });

    it('rejects invalid email addresses', () => {
      const invalidEmails = [
        'invalid',
        '@example.com',
        'test@',
        'test..test@example.com',
        'test@example',
        'test@.example.com',
        ''
      ];
      
      invalidEmails.forEach(email => {
        expect(validateEmail(email)).toBe(false);
      });
    });

    it('handles null and undefined inputs', () => {
      expect(validateEmail(null)).toBe(false);
      expect(validateEmail(undefined)).toBe(false);
    });

    it('provides detailed validation results', () => {
      const result = validateEmail('invalid@', { detailed: true });
      
      expect(result).toMatchObject({
        isValid: false,
        errors: expect.arrayContaining(['Invalid domain format'])
      });
    });
  });

  describe('validatePassword', () => {
    it('validates strong passwords', () => {
      const strongPasswords = [
        'StrongPass123!',
        'MyP@ssw0rd2024',
        'C0mpl3x!Password'
      ];
      
      strongPasswords.forEach(password => {
        const result = validatePassword(password);
        expect(result.isValid).toBe(true);
      });
    });

    it('rejects weak passwords', () => {
      const weakPasswords = [
        'password',           // No uppercase, numbers, symbols
        'PASSWORD',           // No lowercase, numbers, symbols
        'Password',           // No numbers, symbols
        'Pass123',            // Too short
        '12345678',           // No letters, symbols
        ''                   // Empty
      ];
      
      weakPasswords.forEach(password => {
        const result = validatePassword(password);
        expect(result.isValid).toBe(false);
      });
    });

    it('provides specific error messages', () => {
      const result = validatePassword('weak');
      
      expect(result.errors).toEqual(
        expect.arrayContaining([
          'Password must be at least 8 characters long',
          'Password must contain at least one uppercase letter',
          'Password must contain at least one number',
          'Password must contain at least one special character'
        ])
      );
    });

    it('handles custom password requirements', () => {
      const customRules = {
        minLength: 12,
        requireUppercase: true,
        requireNumbers: true,
        requireSymbols: false
      };
      
      const result = validatePassword('GoodPassword123', customRules);
      expect(result.isValid).toBe(true);
      
      const shortResult = validatePassword('Short1', customRules);
      expect(shortResult.isValid).toBe(false);
      expect(shortResult.errors).toContain('Password must be at least 12 characters long');
    });
  });

  describe('validatePhoneNumber', () => {
    it('validates US phone numbers', () => {
      const validNumbers = [
        '+1-555-123-4567',
        '(555) 123-4567',
        '555.123.4567',
        '5551234567',
        '+15551234567'
      ];
      
      validNumbers.forEach(number => {
        expect(validatePhoneNumber(number, 'US')).toBe(true);
      });
    });

    it('validates international phone numbers', () => {
      const validInternational = [
        '+44 20 7946 0958',     // UK
        '+33 1 42 86 83 26',    // France
        '+81 3-1234-5678',      // Japan
        '+86 138 0013 8000'     // China
      ];
      
      validInternational.forEach(number => {
        expect(validatePhoneNumber(number, 'international')).toBe(true);
      });
    });

    it('rejects invalid phone numbers', () => {
      const invalidNumbers = [
        '123',
        'abc-def-ghij',
        '+1-555-123',
        '555-123-456789',
        ''
      ];
      
      invalidNumbers.forEach(number => {
        expect(validatePhoneNumber(number)).toBe(false);
      });
    });

    it('formats valid phone numbers', () => {
      const result = validatePhoneNumber('5551234567', 'US', { format: true });
      
      expect(result).toMatchObject({
        isValid: true,
        formatted: '(555) 123-4567'
      });
    });
  });

  describe('validateURL', () => {
    it('validates correct URLs', () => {
      const validUrls = [
        'https://example.com',
        'http://test.com/path?param=value',
        'https://sub.domain.co.uk:8080/path#anchor',
        'ftp://files.example.com/file.txt'
      ];
      
      validUrls.forEach(url => {
        expect(validateURL(url)).toBe(true);
      });
    });

    it('rejects invalid URLs', () => {
      const invalidUrls = [
        'not-a-url',
        'http://',
        'https://.',
        'ftp://space in url.com',
        ''
      ];
      
      invalidUrls.forEach(url => {
        expect(validateURL(url)).toBe(false);
      });
    });

    it('validates URLs with specific protocols', () => {
      expect(validateURL('https://example.com', ['https'])).toBe(true);
      expect(validateURL('http://example.com', ['https'])).toBe(false);
      expect(validateURL('ftp://files.com', ['http', 'https', 'ftp'])).toBe(true);
    });

    it('validates domain restrictions', () => {
      const options = {
        allowedDomains: ['example.com', 'trusted.org']
      };
      
      expect(validateURL('https://example.com/path', options)).toBe(true);
      expect(validateURL('https://malicious.com/path', options)).toBe(false);
    });
  });

  describe('validateFormData', () => {
    const validationRules = {
      name: { required: true, minLength: 2, maxLength: 50 },
      email: { required: true, type: 'email' },
      age: { required: false, type: 'number', min: 0, max: 120 },
      website: { required: false, type: 'url' }
    };

    it('validates complete valid form data', () => {
      const formData = {
        name: 'John Doe',
        email: 'john@example.com',
        age: 30,
        website: 'https://johndoe.com'
      };
      
      const result = validateFormData(formData, validationRules);
      
      expect(result.isValid).toBe(true);
      expect(result.errors).toEqual({});
    });

    it('catches required field violations', () => {
      const formData = {
        name: '',
        email: 'john@example.com'
      };
      
      const result = validateFormData(formData, validationRules);
      
      expect(result.isValid).toBe(false);
      expect(result.errors.name).toContain('Name is required');
    });

    it('validates field types correctly', () => {
      const formData = {
        name: 'John Doe',
        email: 'invalid-email',
        age: 'not-a-number',
        website: 'not-a-url'
      };
      
      const result = validateFormData(formData, validationRules);
      
      expect(result.isValid).toBe(false);
      expect(result.errors.email).toContain('Invalid email format');
      expect(result.errors.age).toContain('Age must be a number');
      expect(result.errors.website).toContain('Invalid URL format');
    });

    it('validates length constraints', () => {
      const formData = {
        name: 'J', // Too short
        email: 'john@example.com'
      };
      
      const result = validateFormData(formData, validationRules);
      
      expect(result.errors.name).toContain('Name must be at least 2 characters');
    });

    it('validates number ranges', () => {
      const formData = {
        name: 'John Doe',
        email: 'john@example.com',
        age: 150 // Too high
      };
      
      const result = validateFormData(formData, validationRules);
      
      expect(result.errors.age).toContain('Age must be less than or equal to 120');
    });
  });

  describe('isValidJSON', () => {
    it('validates correct JSON strings', () => {
      const validJSON = [
        '{"name": "test"}',
        '[1, 2, 3]',
        '"simple string"',
        'null',
        'true',
        '123'
      ];
      
      validJSON.forEach(json => {
        expect(isValidJSON(json)).toBe(true);
      });
    });

    it('rejects invalid JSON strings', () => {
      const invalidJSON = [
        '{name: "test"}',     // Unquoted keys
        "{'name': 'test'}",   // Single quotes
        '{name: test}',       // Unquoted values
        '{',                  // Incomplete
        'undefined'           // Invalid value
      ];
      
      invalidJSON.forEach(json => {
        expect(isValidJSON(json)).toBe(false);
      });
    });

    it('handles edge cases', () => {
      expect(isValidJSON('')).toBe(false);
      expect(isValidJSON(null)).toBe(false);
      expect(isValidJSON(undefined)).toBe(false);
    });

    it('parses and returns JSON when valid', () => {
      const jsonString = '{"name": "test", "value": 123}';
      const result = isValidJSON(jsonString, { parse: true });
      
      expect(result).toEqual({
        isValid: true,
        data: { name: 'test', value: 123 }
      });
    });
  });
});
```

---

## Utility with External Dependencies Template

Use this for utility functions that depend on external libraries or APIs.

```typescript
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { yourExternalUtility } from '../../utils/yourExternalUtility';

// Mock external dependencies
vi.mock('external-library', () => ({
  externalFunction: vi.fn(),
  ExternalClass: vi.fn().mockImplementation(() => ({
    method: vi.fn()
  }))
}));

vi.mock('../../api/endpoints', () => ({
  fetchExternalData: vi.fn()
}));

import { externalFunction, ExternalClass } from 'external-library';
import { fetchExternalData } from '../../api/endpoints';

const mockExternalFunction = vi.mocked(externalFunction);
const mockExternalClass = vi.mocked(ExternalClass);
const mockFetchExternalData = vi.mocked(fetchExternalData);

describe('yourExternalUtility', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('integrates with external library correctly', () => {
    mockExternalFunction.mockReturnValue('mocked-result');
    
    const result = yourExternalUtility('test-input');
    
    expect(mockExternalFunction).toHaveBeenCalledWith('test-input');
    expect(result).toBe('processed-mocked-result');
  });

  it('handles external library errors', () => {
    mockExternalFunction.mockImplementation(() => {
      throw new Error('External library error');
    });
    
    const result = yourExternalUtility('test-input');
    
    expect(result).toBeNull();
    // Should not throw, should handle gracefully
  });

  it('uses external class correctly', () => {
    const mockInstance = {
      method: vi.fn().mockReturnValue('class-result')
    };
    mockExternalClass.mockReturnValue(mockInstance);
    
    const result = yourExternalUtility('test-input', { useClass: true });
    
    expect(mockExternalClass).toHaveBeenCalledWith(expect.any(Object));
    expect(mockInstance.method).toHaveBeenCalled();
    expect(result).toBe('processed-class-result');
  });

  it('handles async external dependencies', async () => {
    mockFetchExternalData.mockResolvedValue({ data: 'async-result' });
    
    const result = await yourExternalUtility('test-input', { async: true });
    
    expect(mockFetchExternalData).toHaveBeenCalledWith('test-input');
    expect(result).toBe('processed-async-result');
  });

  it('handles network failures gracefully', async () => {
    mockFetchExternalData.mockRejectedValue(new Error('Network error'));
    
    const result = await yourExternalUtility('test-input', { async: true });
    
    expect(result).toBeNull();
    // Should handle network errors without throwing
  });

  it('caches external API results', async () => {
    mockFetchExternalData.mockResolvedValue({ data: 'cached-result' });
    
    // First call
    const result1 = await yourExternalUtility('same-input', { cache: true });
    
    // Second call with same input
    const result2 = await yourExternalUtility('same-input', { cache: true });
    
    expect(result1).toBe(result2);
    expect(mockFetchExternalData).toHaveBeenCalledTimes(1); // Should be cached
  });

  it('handles different external library versions', () => {
    // Test backward compatibility
    mockExternalFunction.mockImplementation((input, options) => {
      if (options?.version === 'v2') {
        return 'v2-result';
      }
      return 'v1-result';
    });
    
    const resultV1 = yourExternalUtility('input', { version: 'v1' });
    const resultV2 = yourExternalUtility('input', { version: 'v2' });
    
    expect(resultV1).toContain('v1-result');
    expect(resultV2).toContain('v2-result');
  });

  it('validates external dependency responses', () => {
    mockExternalFunction.mockReturnValue(null);
    
    const result = yourExternalUtility('test-input');
    
    expect(result).toBeNull();
    // Should validate and handle invalid responses
  });
});
```

---

## Best Practices for Utility Testing

1. **Test pure functions thoroughly** - Same input should always produce same output
2. **Cover edge cases** - Empty inputs, null/undefined, boundary values
3. **Test input validation** - How functions handle invalid or unexpected inputs
4. **Mock external dependencies** - Keep tests isolated and fast
5. **Test error scenarios** - Functions should handle errors gracefully
6. **Verify immutability** - Ensure functions don't mutate input parameters
7. **Test performance** - For complex transformations, consider performance tests
8. **Document expected behavior** - Use descriptive test names and comments
9. **Group related tests** - Use describe blocks to organize test suites
10. **Test both positive and negative cases** - Valid and invalid scenarios

---

**Last Updated**: February 2026
