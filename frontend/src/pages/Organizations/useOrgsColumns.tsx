import React, { useMemo } from 'react';
import { useHistory } from 'react-router-dom';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import EditNoteOutlinedIcon from '@mui/icons-material/EditNoteOutlined';
import { GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { textFilterOperators } from '@/utils/transformTableData';
import { ROUTES } from '@/constants/routes';

export const useOrgsColumns = (): GridColDef[] => {
  const history = useHistory();
  return useMemo(
    () => [
      {
        field: 'name',
        headerName: 'Organization',
        minWidth: 100,
        flex: 2,
        filterOperators: textFilterOperators,
        renderCell: (cellValues: GridRenderCellParams) => {
          return (
            <Box
              component="span"
              aria-label={`Organization Name: ${cellValues.row.name}`}
            >
              {cellValues.row.name}
            </Box>
          );
        }
      },
      {
        field: 'acronym',
        headerName: 'Acronym',
        minWidth: 100,
        flex: 1,
        filterOperators: textFilterOperators,
        renderCell: (cellValues: GridRenderCellParams) => {
          return (
            <Box
              component="span"
              aria-label={`Acronym Name: ${cellValues.row.acronym}`}
            >
              {cellValues.row.acronym}
            </Box>
          );
        }
      },
      {
        field: 'state',
        headerName: 'State',
        minWidth: 100,
        flex: 1,
        filterOperators: textFilterOperators,
        renderCell: (cellValues: GridRenderCellParams) => {
          return (
            <Box
              component="span"
              aria-label={`State for Organization ${cellValues.row.name}: ${cellValues.row.state}`}
            >
              {cellValues.row.state}
            </Box>
          );
        }
      },
      {
        field: 'region_id',
        headerName: 'Region',
        minWidth: 100,
        flex: 1,
        filterOperators: textFilterOperators,
        renderCell: (cellValues: GridRenderCellParams) => {
          return (
            <Box
              component="span"
              aria-label={`Region for Organization ${cellValues.row.name}: ${cellValues.row.region_id}`}
            >
              {cellValues.row.region_id}
            </Box>
          );
        }
      },
      {
        field: 'view',
        headerName: 'View/Edit',
        width: 100,
        disableExport: true,
        sortable: false,
        filterable: false,
        disableColumnMenu: true,
        renderCell: (cellValues: GridRenderCellParams) => {
          return (
            <IconButton
              color="primary"
              aria-label={`View or Edit Organization ${cellValues.row.name}`}
              aria-describedby={`description-${cellValues.row.id}`}
              onClick={() =>
                history.push(
                  ROUTES.ORGANIZATION.replace(
                    ':organizationId',
                    cellValues.row.id
                  )
                )
              }
            >
              <EditNoteOutlinedIcon />
            </IconButton>
          );
        }
      }
    ],
    [history]
  );
};
