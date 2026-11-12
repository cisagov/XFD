import React, { useState } from 'react';

// Material-UI Components
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';

// DataGrid Components
import type { GridColDef, GridFilterModel } from '@mui/x-data-grid';

// Components
import CustomDataGrid from '../DataGrid/CustomDataGrid';
import CustomToolbar from '../DataGrid/CustomToolbar';
import {
  DATA_GRID_PAGE_SIZE_OPTIONS,
  DEFAULT_DATA_GRID_PAGE_SIZE
} from '@/constants/dataGrid';
import { cleanFilterModelItems, isFilterModelEmpty } from '@/utils/tableUtils';

interface NotificationTableProps {
  title: string;
  rows: any[];
  columns: GridColDef[];
  tableStyling?: object;
  hideFooterPagination?: boolean;
  children?: React.ReactNode; // For extra info below the table
}

const NotificationTable: React.FC<NotificationTableProps> = ({
  title,
  rows,
  columns,
  tableStyling,
  hideFooterPagination = false,
  children
}) => {
  const [filterModel, setFilterModel] = useState<GridFilterModel>({
    items: []
  });
  const [hasActiveFilters, setHasActiveFilters] = useState(false);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" pb={2} fontWeight="500">
        {title}
      </Typography>
      <CustomDataGrid
        rows={rows}
        columns={columns}
        getRowHeight={() => 'auto'}
        sx={tableStyling}
        hideFooterPagination={hideFooterPagination}
        disableRowSelectionOnClick
        filterModel={filterModel}
        onFilterModelChange={(model) => {
          const cleanedModel = cleanFilterModelItems(model, filterModel);
          setFilterModel(cleanedModel);
          setHasActiveFilters(!isFilterModelEmpty(cleanedModel));
        }}
        slots={{ toolbar: CustomToolbar }}
        slotProps={{
          toolbar: {
            disableExport: true,
            exportTitle: title,
            hasActiveFilters
          } as any,
          basePopper: {
            placement: 'bottom-start'
          }
        }}
        initialState={{
          pagination: {
            paginationModel: { pageSize: DEFAULT_DATA_GRID_PAGE_SIZE }
          }
        }}
        pageSizeOptions={DATA_GRID_PAGE_SIZE_OPTIONS}
        showToolbar
      />
      {children}
    </Paper>
  );
};

export default NotificationTable;
