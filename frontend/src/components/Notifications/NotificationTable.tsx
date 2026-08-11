import React from 'react';

// Material-UI Components
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';

// DataGrid Components
import { GridColDef } from '@mui/x-data-grid';

// Components
import CustomDataGrid from '../DataGrid/CustomDataGrid';

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
}) => (
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
    />
    {children}
  </Paper>
);

export default NotificationTable;
