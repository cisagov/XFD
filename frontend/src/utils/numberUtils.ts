/**
 * Formats a number with comma separators for readability.
 * 
 * Per CRASM-3568 requirements:
 * - Numbers >= 1,000 will have comma separators (e.g., 1,000; 1,000,000; 1,000,000,000)
 * - Numbers < 1,000 remain unchanged (e.g., 999 stays 999)
 * - Formatting affects only display, not calculations, sorting, or data storage
 * 
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
