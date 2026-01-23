// React
import React from 'react';

// MUI Components
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import { GridColDef, GridRenderCellParams } from '@mui/x-data-grid';

// Utils
import { textFilterOperators } from '@/utils/transformTableData';

export const getPendingUserColumns = ({
  userType,
  handleApproveClick,
  handleDenyClick
}: {
  userType?: string;
  handleApproveClick: (row: any) => void;
  handleDenyClick: (row: any) => void;
}): GridColDef[] => {
  const columns: GridColDef[] = [
    {
      field: 'full_name',
      headerName: 'Name',
      minWidth: 100,
      flex: 1.1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Full Name for User: ${cellValues.row.full_name}`}
          >
            {cellValues.row.full_name}
          </Box>
        );
      }
    },
    {
      field: 'email',
      headerName: 'Email',
      minWidth: 100,
      flex: 1.5,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Email for User ${cellValues.row.full_name}: ${cellValues.row.email}`}
          >
            {cellValues.row.email}
          </Box>
        );
      }
    },
    {
      field: 'region_id',
      headerName: 'Region',
      minWidth: 50,
      flex: 0.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Region ID for User ${cellValues.row.full_name}: ${cellValues.row.region_id}`}
          >
            {cellValues.row.region_id}
          </Box>
        );
      }
    },
    {
      field: 'state',
      headerName: 'State',
      minWidth: 80,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`State for User ${cellValues.row.full_name}: ${cellValues.row.state}`}
          >
            {cellValues.row.state}
          </Box>
        );
      }
    },
    {
      field: 'created_at',
      headerName: 'Created At',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Created At Date for User ${cellValues.row.full_name}: ${cellValues.row.created_at}`}
          >
            {cellValues.row.created_at}
          </Box>
        );
      }
    },
    {
      field: 'cognito_use_case_description',
      headerName: 'Use Case',
      minWidth: 150,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Use Case for ${cellValues.row.full_name}: ${cellValues.row.cognito_use_case_description}`}
          >
            {cellValues.row.cognito_use_case_description}
          </Box>
        );
      }
    },
    {
      field: 'status',
      headerName: 'Registration Status',
      minWidth: 250,
      flex: 2,
      filterable: false,
      sortable: false,
      disableColumnMenu: true,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Stack direction="row" spacing={2} p={1}>
            <Button
              variant="approve"
              onClick={() => handleApproveClick(cellValues.row)}
              disabled={userType === 'globalView'}
              aria-label={`Approve User: ${cellValues.row.full_name}`}
            >
              Approve
            </Button>
            <Button
              variant="deny"
              onClick={() => handleDenyClick(cellValues.row)}
              disabled={userType === 'globalView'}
              aria-label={`Deny User: ${cellValues.row.full_name}`}
            >
              Deny
            </Button>
          </Stack>
        );
      }
    }
  ];
  return columns;
};

export const getMemberUserColumns = (): GridColDef[] => {
  const columns: GridColDef[] = [
    {
      field: 'full_name',
      headerName: 'Name',
      minWidth: 100,
      flex: 1.5,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Full Name for User: ${cellValues.row.full_name}`}
          >
            {cellValues.row.full_name}
          </Box>
        );
      }
    },
    {
      field: 'email',
      headerName: 'Email',
      minWidth: 100,
      flex: 2,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Email for User ${cellValues.row.full_name}: ${cellValues.row.email}`}
          >
            {cellValues.row.email}
          </Box>
        );
      }
    },
    {
      field: 'region_id',
      headerName: 'Region',
      minWidth: 50,
      flex: 0.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Region ID for User ${cellValues.row.full_name}: ${cellValues.row.region_id}`}
          >
            {cellValues.row.region_id}
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
            aria-label={`State for User ${cellValues.row.full_name}: ${cellValues.row.state}`}
          >
            {cellValues.row.state}
          </Box>
        );
      }
    },
    {
      field: 'last_logged_in',
      headerName: 'Last Logged In',
      minWidth: 80,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Last Logged In Date for User ${cellValues.row.full_name}: ${cellValues.row.last_logged_in}`}
          >
            {cellValues.row.last_logged_in}
          </Box>
        );
      }
    },
    {
      field: 'organizations_display',
      headerName: 'Organizations',
      minWidth: 250,
      flex: 2,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`Organizations for User ${cellValues.row.full_name}: ${cellValues.row.organizations_display}`}
        >
          {cellValues.row.organizations_display}
        </Box>
      )
    },
    {
      field: 'org_acronym',
      headerName: 'Org Acronym',
      minWidth: 100,
      flex: 0.5,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`Organization acronym for User ${cellValues.row.full_name}: ${cellValues.row.org_acronym}`}
        >
          {cellValues.row.org_acronym}
        </Box>
      )
    }
  ];

  return columns;
};

export const organizationCols: GridColDef[] = [
  {
    field: 'name',
    headerName: 'Organization Name',
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
    headerName: 'Org Acronym',
    minWidth: 100,
    flex: 1,
    filterOperators: textFilterOperators,
    renderCell: (cellValues: GridRenderCellParams) => {
      return (
        <Box
          component="span"
          aria-label={`Organization Acronym: ${cellValues.row.acronym}`}
        >
          {cellValues.row.acronym}
        </Box>
      );
    }
  },
  {
    field: 'updated_at',
    headerName: 'Updated At',
    minWidth: 100,
    flex: 1,
    renderCell: (cellValues: GridRenderCellParams) => {
      return (
        <Box
          component="span"
          aria-label={`Date Updated At for Organization ${cellValues.row.name}: ${cellValues.row.updated_at}`}
        >
          {cellValues.row.updated_at}
        </Box>
      );
    }
  },
  {
    field: 'state_name',
    headerName: 'State',
    minWidth: 100,
    flex: 1,
    filterOperators: textFilterOperators,
    renderCell: (cellValues: GridRenderCellParams) => {
      return (
        <Box
          component="span"
          aria-label={`State Name for Organization ${cellValues.row.name}: ${cellValues.row.state_name}`}
        >
          {cellValues.row.state_name}
        </Box>
      );
    }
  }
];
