import React from 'react';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import EditNoteOutlined from '@mui/icons-material/EditNoteOutlined';
import Delete from '@mui/icons-material/Delete';
import {
  GridColDef,
  GridRenderCellParams,
  getGridStringOperators
} from '@mui/x-data-grid';
import { format } from 'date-fns';

// Only allow equals + contains for string filters
const getTextFilterOperators = () =>
  getGridStringOperators().filter(
    (op) => op.value === 'equals' || op.value === 'contains'
  );
const textFilterOperators = getTextFilterOperators();

type UseUserColumnsProps = {
  user: { user_type?: string } | null | undefined;
  setSelectedRow: (row: any) => void;
  setFormValues: (values: any) => void;
  setEditUserDialogOpen: (open: boolean) => void;
  setDeleteUserDialogOpen: (open: boolean) => void;
};

export const useUserColumns = ({
  user,
  setSelectedRow,
  setFormValues,
  setEditUserDialogOpen,
  setDeleteUserDialogOpen
}: UseUserColumnsProps): GridColDef[] => {
  const columns: GridColDef[] = [
    {
      field: 'full_name',
      headerName: 'Name',
      minWidth: 100,
      flex: 0.9,
      filterOperators: textFilterOperators,
      renderCell: ({ row }: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`Full Name for User: ${row.full_name}`}
        >
          {row.full_name}
        </Box>
      )
    },
    {
      field: 'email',
      headerName: 'Email',
      minWidth: 100,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: ({ row }: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`Email for User ${row.full_name}: ${row.email}`}
        >
          {row.email}
        </Box>
      )
    },
    {
      field: 'region_id',
      headerName: 'Region',
      minWidth: 50,
      flex: 0.4,
      filterOperators: textFilterOperators,
      renderCell: ({ row }: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`Region for User ${row.full_name}: ${row.region_id}`}
        >
          {row.region_id}
        </Box>
      )
    },
    {
      field: 'orgs',
      headerName: 'Organization',
      minWidth: 100,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: ({ row }: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`Organizations for User ${row.full_name}: ${row.orgs}`}
        >
          {row.orgs}
        </Box>
      )
    },
    {
      field: 'org_acronym',
      headerName: 'Org Acronym',
      minWidth: 100,
      flex: 0.5,
      filterOperators: textFilterOperators,
      renderCell: ({ row }: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`Organization acronym ${row.full_name}: ${row.org_acronym}`}
        >
          {row.org_acronym}
        </Box>
      )
    },
    {
      field: 'user_type',
      headerName: 'User Type',
      minWidth: 100,
      flex: 0.7,
      filterOperators: textFilterOperators,
      renderCell: ({ row }: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`User Type for User ${row.full_name}: ${row.user_type}`}
        >
          {row.user_type}
        </Box>
      )
    },
    {
      field: 'date_approved',
      headerName: 'Approval Date',
      minWidth: 100,
      flex: 0.7,
      type: 'string',
      filterOperators: textFilterOperators,
      renderCell: ({ row }: GridRenderCellParams) => {
        const dateApproved = row?.date_approved;
        return (
          <Tooltip
            title={
              dateApproved
                ? format(new Date(dateApproved), 'MM-dd-yyyy hh:mm a')
                : 'None'
            }
          >
            <Box component="span">
              {dateApproved
                ? format(new Date(dateApproved), 'MM-dd-yyyy hh:mm a')
                : 'None'}
            </Box>
          </Tooltip>
        );
      }
    },
    {
      field: 'approved_by',
      headerName: 'Approved By',
      minWidth: 100,
      flex: 0.7,
      filterOperators: textFilterOperators,
      renderCell: ({ row }: GridRenderCellParams) => {
        const approvedBy = row?.approved_by;
        const fullName = approvedBy?.full_name ?? 'None';

        return (
          <Tooltip
            title={
              approvedBy
                ? `${approvedBy.full_name} ${approvedBy.email}`
                : 'None'
            }
          >
            <Box component="span">{fullName}</Box>
          </Tooltip>
        );
      }
    },
    {
      field: 'lastLoggedInString',
      headerName: 'Last Logged In',
      minWidth: 100,
      flex: 0.7,
      type: 'string',
      filterOperators: textFilterOperators,
      sortComparator: (v1, v2) => {
        if (v1 === 'None') return -1;
        if (v2 === 'None') return 1;
        return new Date(v1).getTime() - new Date(v2).getTime();
      },
      renderCell: ({ row }: GridRenderCellParams) => (
        <Box component="span">{row.lastLoggedInString}</Box>
      )
    },
    {
      field: 'edit',
      headerName: 'View/Edit',
      minWidth: 50,
      flex: 0.5,
      disableExport: true,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: GridRenderCellParams) => (
        <IconButton
          aria-label={`View or Edit User ${row.full_name}`}
          onClick={() => {
            setSelectedRow(row);
            setFormValues({
              id: row.id,
              first_name: row.first_name,
              last_name: row.last_name,
              email: row.email,
              user_type: row.user_type,
              state: row.state || '',
              region_id: row.region_id || '',
              org_name: row.roles[0]?.organization?.name || '',
              org_id: row.roles[0]?.organization?.id || '',
              originalOrgId: row.roles[0]?.organization?.id || '',
              originalRoleId: row.roles[0]?.id || ''
            });
            setEditUserDialogOpen(true);
          }}
        >
          <EditNoteOutlined />
        </IconButton>
      )
    }
  ];

  if (user?.user_type === 'globalAdmin') {
    columns.push({
      field: 'delete',
      headerName: 'Delete',
      minWidth: 50,
      flex: 0.4,
      disableExport: true,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: GridRenderCellParams) => (
        <IconButton
          aria-label={`Delete user ${row.full_name}`}
          onClick={() => {
            setSelectedRow(row);
            setDeleteUserDialogOpen(true);
          }}
        >
          <Delete />
        </IconButton>
      )
    });
  }

  return columns;
};
