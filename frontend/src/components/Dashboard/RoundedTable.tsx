import React from 'react';
import {
  Alert,
  Box,
  Card,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from '@mui/material';
import { SxProps } from '@mui/system';

type ColumnConfig<T> = {
  key: keyof T;
  header: string;
  textAlign?: 'left' | 'center' | 'right';
  minWidth?: number | string;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
  headerPadding?: number;
};

type RoundedTableProps<T> = {
  columns: ColumnConfig<T>[];
  data: T[];
  noDataMessage?: string | React.ReactNode;
  tableStyles?: SxProps;
  rowHeadStyles?: SxProps;
  rowBodyStyles?: SxProps;
  cellBodyStyles?: SxProps;
};

const tableSx: SxProps = {
  borderCollapse: 'separate',
  borderSpacing: '0 16px',
  width: '100%',
  tableLayout: 'auto',
  display: { xs: 'none', sm: 'table' }
};

const rowHeadSx: SxProps = {
  '& th': {
    border: 'none',
    backgroundColor: 'transparent',
    pb: 0,
    fontSize: '11px',
    fontWeight: 600
  }
};

const rowBodySx = {
  borderRadius: 5,
  borderColor: 'gray',
  '& td': {
    borderLeft: '1px solid #ccc',
    backgroundColor: '#fff',
    py: '5px',
    px: 2
  },
  '& td:first-of-type': {
    borderTopLeftRadius: 8,
    borderBottomLeftRadius: 8
  },
  '& td:last-of-type': {
    borderTopRightRadius: 8,
    borderBottomRightRadius: 8
  }
};

const cellBodySx = {
  border: '1px solid',
  borderColor: 'neutrals.light',
  height: '64px'
};

export default function RoundedTable<T extends Record<string, any>>({
  columns,
  data,
  noDataMessage = 'No data available.',
  tableStyles = tableSx,
  rowHeadStyles = rowHeadSx,
  rowBodyStyles = rowBodySx,
  cellBodyStyles = cellBodySx
}: RoundedTableProps<T>) {
  if (data.length === 0) {
    return (
      <Alert severity="info" sx={{ width: '100%', mt: 2 }}>
        {noDataMessage}
      </Alert>
    );
  }

  return (
    <>
      <Table sx={tableStyles} component="table">
        <TableHead component="thead">
          <TableRow sx={rowHeadStyles} component="tr">
            {columns.map((col, colIndex) => (
              <TableCell
                key={colIndex}
                sx={{
                  minWidth: col.minWidth || '66px',
                  p: col.headerPadding || 0
                }}
                align={col.textAlign || 'left'}
                component="th"
                scope="col"
              >
                {col.header}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody component="tbody">
          {data.map((row, rowIndex) => (
            <TableRow key={rowIndex} sx={rowBodyStyles} component="tr">
              {columns.map((col, colIndex) => (
                <TableCell
                  key={colIndex}
                  sx={cellBodyStyles}
                  align={col.textAlign || 'left'}
                  tabIndex={0}
                  role="cell"
                  aria-label={col.header + ' ' + row[col.key]}
                  component="td"
                >
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Box sx={{ display: { xs: 'block', sm: 'none' }, textAlign: 'center' }}>
        {data.map((row, rowIndex) => (
          <Card
            key={rowIndex}
            sx={{
              mb: 2,
              pt: 1,
              px: 0,
              borderColor: 'neutrals.light',
              borderRadius: 2
            }}
            variant="outlined"
          >
            {columns.map((col, colIndex) => (
              <Box key={colIndex}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  align="center"
                  component="div"
                >
                  {col.header}
                </Typography>
                <Typography
                  component="div"
                  variant="body2"
                  align="center"
                  sx={{ py: 2 }}
                >
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </Typography>
                {colIndex < columns.length - 1 && (
                  <Divider sx={{ my: 1, borderColor: 'neutrals.light' }} />
                )}
              </Box>
            ))}
          </Card>
        ))}
      </Box>
    </>
  );
}
