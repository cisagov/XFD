import React from 'react';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { DataGrid, GridColDef } from '@mui/x-data-grid';

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
    <DataGrid
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
