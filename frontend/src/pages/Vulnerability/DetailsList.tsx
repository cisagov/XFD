import React from 'react';
import {
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow
} from '@mui/material';
import { tableCellClasses } from '@mui/material/TableCell';

const DetailsList = ({ data }: { data: Record<string, React.ReactNode> }) => (
  <Grid
    size={{ sm: 12, md: 6 }}
    sx={{ display: 'flex', justifyContent: 'left' }}
  >
    <TableContainer sx={{ ml: -2 }}>
      <Table
        size="small"
        sx={{
          [`& .${tableCellClasses.root}`]: {
            borderBottom: 'none',
            fontSize: 15
          },
          width: 'auto'
        }}
      >
        <TableBody>
          {Object.entries(data)
            .filter(([_, value]) => {
              if (value === null || value === undefined) return false;
              if (typeof value === 'string' && value.trim() === '')
                return false;
              return true;
            })
            .map(([header, value]) => (
              <TableRow key={header}>
                <TableCell
                  align="right"
                  sx={{ fontWeight: 600, verticalAlign: 'top' }}
                >
                  {header}:
                </TableCell>
                <TableCell>{value}</TableCell>
              </TableRow>
            ))}
        </TableBody>
      </Table>
    </TableContainer>
  </Grid>
);

export default DetailsList;
