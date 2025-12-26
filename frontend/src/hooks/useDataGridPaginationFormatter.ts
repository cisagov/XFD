/**
 * Path: frontend/src/hooks/useDataGridPaginationFormatter.ts
 * Author: Jesse Salinas
 * Date: 2025-12-23
 * Description: Custom hook for formatting MUI DataGrid pagination display with comma separators.
 *
 */

/**
 * Custom hook for formatting MUI DataGrid pagination display with comma separators.
 * Since MUI DataGrid localeText is complex to customize, this hook updates
 * the pagination display after render using DOM manipulation.
 */
import { useEffect } from 'react';
import { formatCount } from '../utils/numberUtils';

/**
 * Hook to format DataGrid pagination numbers after component renders
 * This finds the pagination text and replaces it with formatted versions
 */
export const useDataGridPaginationFormatter = (isLoading: boolean) => {
  useEffect(() => {
    if (isLoading) return;

    // Small delay to ensure DataGrid has rendered
    const timer = setTimeout(() => {
      const paginationLabels = document.querySelectorAll(
        '.MuiTablePagination-displayedRows'
      );
      paginationLabels.forEach((label) => {
        const text = label.textContent;
        if (text && /\d+–\d+ of \d+/.test(text)) {
          const match = text.match(/(\d+)–(\d+) of (\d+)/);
          if (match) {
            const [, from, to, count] = match;
            label.textContent = `${formatCount(parseInt(from))}–${formatCount(parseInt(to))} of ${formatCount(parseInt(count))}`;
          }
        }
      });
    }, 100);

    return () => clearTimeout(timer);
  }, [isLoading]);
};
