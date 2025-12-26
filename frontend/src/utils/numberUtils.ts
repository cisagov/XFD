/**
 * Path: frontend/src/utils/numberUtils.ts
 * Author: Jesse Salinas
 * Date: 2025-12-23
 * Description: Formats a number with comma separators for readability.
 *
 */

/**
 * @param value - The numeric value to format
 * @returns The formatted string with comma separators if >= 1,000, otherwise the original number as string
 *
 * @example
 * formatCount(999)        // "999"
 * formatCount(1000)       // "1,000"
 * formatCount(1500)       // "1,500"
 * formatCount(1000000)    // "1,000,000"
 * formatCount(null)       // "0"
 * formatCount(undefined)  // "0"
 */
export function formatCount(value: number | null | undefined): string {
  // Handle null, undefined, and NaN values
  if (value == null || isNaN(value)) {
    return '0';
  }

  // For numbers >= 1,000, use toLocaleString to add comma separators
  if (Math.abs(value) >= 1000) {
    return value.toLocaleString('en-US');
  }

  // For numbers < 1,000, return as string without formatting
  return value.toString();
}
