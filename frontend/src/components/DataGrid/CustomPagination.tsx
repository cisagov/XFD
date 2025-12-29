/**
 * Path: frontend/src/components/DataGrid/CustomPagination.tsx
 * Author: Jesse Salinas
 * Date: 2025-12-26
 * Description: Custom pagination component for MUI DataGrid with comma-formatted numbers.
 *
 * This component replaces the default DataGrid pagination to format numbers >= 1,000
 * with comma separators for improved readability while preserving numbers < 1,000 unchanged.
 *
 * Usage: Add to DataGrid slots prop: slots={{ pagination: CustomPagination }}
 */

import React from 'react';
import TablePagination from '@mui/material/TablePagination';
import {
  gridPageSelector,
  gridPageSizeSelector,
  gridRowCountSelector,
  useGridApiContext,
  useGridSelector
} from '@mui/x-data-grid';

// Utils
import { formatDisplayValue } from 'utils/stringUtils';

/**
 * Custom pagination component for DataGrid with comma-formatted numbers
 * Integrates with MUI DataGrid state management through grid selectors and API context
 */
const CustomPagination: React.FC = () => {
  const apiRef = useGridApiContext();
  const page = useGridSelector(apiRef, gridPageSelector);
  const pageSize = useGridSelector(apiRef, gridPageSizeSelector);
  const rowCount = useGridSelector(apiRef, gridRowCountSelector);

  const handlePageChange = (
    event: React.MouseEvent<HTMLButtonElement> | null,
    newPage: number
  ) => {
    apiRef.current.setPage(newPage);
  };

  const handlePageSizeChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const newPageSize = parseInt(event.target.value, 10);
    apiRef.current.setPageSize(newPageSize);
  };

  /**
   * Format the pagination display range with comma separators
   * Example: "1–15 of 5,565" instead of "1–15 of 5565"
   */
  const formatDisplayedRows = ({
    from,
    to,
    count
  }: {
    from: number;
    to: number;
    count: number;
  }) =>
    `${formatDisplayValue(from)}–${formatDisplayValue(to)} of ${formatDisplayValue(count)}`;

  return (
    <TablePagination
      component="div"
      count={rowCount}
      page={page}
      rowsPerPage={pageSize}
      onPageChange={handlePageChange}
      onRowsPerPageChange={handlePageSizeChange}
      labelDisplayedRows={formatDisplayedRows}
      rowsPerPageOptions={[15, 30, 50, 100]}
    />
  );
};

export default CustomPagination;
