import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutline';
import Delete from '@mui/icons-material/Delete';
import EditNoteOutlined from '@mui/icons-material/EditNoteOutlined';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import InfoDialog from 'components/Dialog/InfoDialog';
import {
  initialUserFormValues,
  initializeUser,
  User,
  UserFormValues
} from 'types';
import { useAuthContext } from 'context';
import UserForm from './UserForm';
import { useUserApi, UserType } from '@/hooks/useUserApi';

type ApiErrorStates = {
  getUsersError: string;
  getAddUserError: string;
  getDeleteError: string;
  getUpdateUserError: string;
  getOrgsError: string;
};

export interface ApiResponse {
  result: User[];
  count: number;
  url?: string;
}

export const Users: React.FC = () => {
  const { user } = useAuthContext();
  const {
    users,
    isLoading,
    error: getUsersError,
    setUsers,
    fetchUsers,
    deleteUser
  } = useUserApi();
  const [selectedRow, setSelectedRow] = useState<UserType>(initializeUser);
  const [editUserDialogOpen, setEditUserDialogOpen] = useState(false);
  const [deleteUserDialogOpen, setDeleteUserDialogOpen] = useState(false);
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [infoDialogContent, setInfoDialogContent] = useState<string>('');
  const [loadingError, setLoadingError] = useState(false);
  const [apiErrorStates, setApiErrorStates] = useState<ApiErrorStates>({
    getUsersError: '',
    getAddUserError: '',
    getDeleteError: '',
    getUpdateUserError: '',
    getOrgsError: ''
  });
  const [formValues, setFormValues] = useState<UserFormValues>(
    initialUserFormValues
  );

  useEffect(() => {
    if (getUsersError) {
      setLoadingError(true);
      setApiErrorStates((prev) => ({ ...prev, getUsersError }));
    } else {
      setLoadingError(false);
      setApiErrorStates((prev) => ({ ...prev, getUsersError: '' }));
    }
  }, [getUsersError]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const userCols: GridColDef[] = [
    {
      field: 'full_name',
      headerName: 'Name',
      minWidth: 100,
      flex: 0.9,
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
      flex: 1,
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
      flex: 0.4,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Region for User ${cellValues.row.full_name}: ${cellValues.row.region_id}`}
          >
            {cellValues.row.region_id}
          </Box>
        );
      }
    },
    {
      field: 'orgs',
      headerName: 'Organization',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Organizations for User ${cellValues.row.full_name}: ${cellValues.row.orgs}`}
          >
            {cellValues.row.orgs}
          </Box>
        );
      }
    },
    {
      field: 'org_acronym',
      headerName: 'Org Acronym',
      minWidth: 100,
      flex: 0.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Organization acronym ${cellValues.row.full_name}: ${cellValues.row.acronym}`}
          >
            {cellValues.row.org_acronym}
          </Box>
        );
      }
    },
    {
      field: 'user_type',
      headerName: 'User Type',
      minWidth: 100,
      flex: 0.7,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`User Type for User ${cellValues.row.full_name}: ${cellValues.row.user_type}`}
          >
            {cellValues.row.user_type}
          </Box>
        );
      }
    },
    {
      field: 'date_approved',
      headerName: 'Approval Date',
      minWidth: 100,
      flex: 0.7,
      renderCell: (params: GridRenderCellParams) => {
        const dateApproved = params.row?.date_approved;
        return (
          <Tooltip
            title={
              dateApproved
                ? format(new Date(dateApproved), 'MM-dd-yyyy hh:mm a')
                : 'None'
            }
          >
            <Box
              component="span"
              aria-label={`Approval Date for User ${params.row.full_name}: ${dateApproved}`}
            >
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
      renderCell: (params: GridRenderCellParams) => {
        const approvedBy = params.row?.approved_by;
        const fullName = approvedBy ? approvedBy.full_name : 'None';

        const fullUserInfo = params.row?.approved_by;
        return (
          <Tooltip
            title={
              fullUserInfo
                ? `${fullUserInfo.full_name} ${fullUserInfo.email}`
                : 'None'
            }
          >
            <Box
              component="span"
              aria-label={`User ${params.row.full_name} approved by: ${fullName}`}
            >
              {fullName}
            </Box>
          </Tooltip>
        );
      }
    },
    {
      field: 'dateToUSigned',
      headerName: 'Date ToU Signed',
      minWidth: 100,
      flex: 1,
      sortComparator: (v1, v2) => {
        if (v1 === 'None') return -1;
        if (v2 === 'None') return 1;

        const date1 = new Date(v1);
        const date2 = new Date(v2);
        return date1.getTime() - date2.getTime();
      },
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Date ToU signed for User ${cellValues.row.full_name}: ${cellValues.row.dateToUSigned}`}
          >
            {cellValues.row.dateToUSigned}
          </Box>
        );
      }
    },
    {
      field: 'accepted_terms_version',
      headerName: 'ToU Version',
      minWidth: 50,
      flex: 0.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`ToU Version for User ${cellValues.row.full_name}: ${cellValues.row.accepted_terms_version}`}
          >
            {cellValues.row.accepted_terms_version}
          </Box>
        );
      }
    },
    {
      field: 'lastLoggedInString',
      headerName: 'Last Logged In',
      minWidth: 100,
      flex: 0.7,
      sortComparator: (v1, v2) => {
        if (v1 === 'None') return -1;
        if (v2 === 'None') return 1;

        const date1 = new Date(v1);
        const date2 = new Date(v2);

        return date1.getTime() - date2.getTime();
      },
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Last Logged In Date for User ${cellValues.row.full_name}: ${cellValues.row.lastLoggedInString}`}
          >
            {cellValues.row.lastLoggedInString}
          </Box>
        );
      }
    },
    {
      field: 'edit',
      headerName: 'View/Edit',
      minWidth: 50,
      flex: 0.5,
      disableExport: true,
      sortable: false,
      filterable: false,
      renderCell: (cellValues: GridRenderCellParams) => {
        const ariaLabel = `View or Edit User ${cellValues.row.full_name}`;
        const descriptionId = `description-${cellValues.row.id}`;
        return (
          <>
            <span id={descriptionId} style={{ display: 'none' }}>
              {`Edit details for user ${cellValues.row.email}`}
            </span>
            <IconButton
              color="primary"
              aria-label={ariaLabel}
              aria-describedby={descriptionId}
              onClick={() => {
                setSelectedRow(cellValues.row);
                setFormValues({
                  id: cellValues.row.id,
                  first_name: cellValues.row.first_name,
                  last_name: cellValues.row.last_name,
                  email: cellValues.row.email,
                  user_type: cellValues.row.user_type,
                  state: cellValues.row.state || '',
                  region_id: cellValues.row.region_id || '',
                  org_name: cellValues.row.roles[0]?.organization?.name || '',
                  org_id: cellValues.row.roles[0]?.organization?.id || '',
                  originalOrgId:
                    cellValues.row.roles[0]?.organization?.id || '',
                  originalRoleId: cellValues.row.roles[0]?.id || ''
                });
                setEditUserDialogOpen(true);
              }}
            >
              <EditNoteOutlined />
            </IconButton>
          </>
        );
      }
    }
  ];
  if (user?.user_type === 'globalAdmin') {
    userCols.push({
      field: 'delete',
      headerName: 'Delete',
      disableExport: true,
      minWidth: 50,
      flex: 0.4,
      sortable: false,
      filterable: false,
      renderCell: (cellValues: GridRenderCellParams) => {
        const ariaLabel = `Delete user ${cellValues.row.full_name}`;
        const descriptionId = `delete-description-${cellValues.row.id}`;
        return (
          <>
            <span id={descriptionId} style={{ display: 'none' }}>
              {`Delete user ${cellValues.row.email}`}
            </span>
            <IconButton
              color="primary"
              aria-label={ariaLabel}
              aria-describedby={descriptionId}
              onClick={() => {
                setSelectedRow(cellValues.row);
                setDeleteUserDialogOpen(true);
              }}
            >
              <Delete />
            </IconButton>
          </>
        );
      }
    });
  }

  const deleteRow = async (row: UserType) => {
    const { success, errorMessage } = await deleteUser(row);
    if (success) {
      setApiErrorStates({ ...apiErrorStates, getDeleteError: '' });
      setInfoDialogContent('This user has been successfully removed.');
      setInfoDialogOpen(true);
    } else {
      setApiErrorStates({ ...apiErrorStates, getDeleteError: errorMessage });
      setInfoDialogContent(
        'This user has been not been removed. Check the console log for more details.'
      );
    }
  };

  const confirmDeleteUserDialog = (
    <ConfirmDialog
      isOpen={deleteUserDialogOpen}
      onConfirm={() => {
        deleteRow(selectedRow);
      }}
      onCancel={() => setDeleteUserDialogOpen(false)}
      title={'Are you sure you want to delete this user?'}
      content={
        <>
          <Typography mb={3}>
            This request will permanently remove <b>{selectedRow?.full_name}</b>{' '}
            from Cyhy Dashboard and cannot be undone.
          </Typography>
          {apiErrorStates.getDeleteError && (
            <Alert severity="error">
              Error removing user: {apiErrorStates.getDeleteError}. See the
              network tab for more details.
            </Alert>
          )}
        </>
      }
      screenWidth="xs"
    />
  );

  const renderUserForm = (
    <UserForm
      users={users}
      setUsers={setUsers}
      values={formValues}
      setValues={setFormValues}
      editUserDialogOpen={editUserDialogOpen}
      setEditUserDialogOpen={setEditUserDialogOpen}
      apiErrorStates={apiErrorStates}
      setApiErrorStates={setApiErrorStates}
      setInfoDialogOpen={setInfoDialogOpen}
      setInfoDialogContent={setInfoDialogContent}
    />
  );

  const mobileMargin = {
    px: {
      xs: 1,
      sm: 1,
      md: 1,
      lg: 1,
      xl: 0
    }
  };

  return (
    <Box
      display="flex"
      flexDirection="column"
      minHeight="100vh"
      maxWidth="1152px"
      width="100%"
      margin="auto"
      pb={6}
    >
      <Typography
        fontSize={34}
        fontWeight="bold"
        letterSpacing={0}
        my={6}
        variant="h1"
        sx={mobileMargin}
      >
        Users
      </Typography>
      {isLoading ? (
        <Paper elevation={2}>
          <Alert severity="info">Loading Users..</Alert>
        </Paper>
      ) : isLoading === false && loadingError ? (
        <Stack direction="row" spacing={2}>
          <Paper elevation={2}>
            <Alert severity="warning">Error Loading Users!</Alert>
          </Paper>
          <Button
            onClick={fetchUsers}
            variant="contained"
            color="primary"
            sx={{ width: 'fit-content' }}
          >
            Retry
          </Button>
        </Stack>
      ) : isLoading === false && loadingError === false ? (
        <Paper elevation={2} sx={{ width: '100%', minHeight: '200px' }}>
          <DataGrid
            rows={users}
            columns={userCols}
            slots={{ toolbar: CustomToolbar }}
            slotProps={{
              toolbar: {
                // Disabling export for users table as per temp solution mentioned in CRASM-2509
                disableExport: true,
                exportTitle: 'Users'
              } as any,
              basePopper: {
                placement: 'bottom-start'
              }
            }}
            initialState={{
              pagination: { paginationModel: { pageSize: 15 } },
              columns: {
                columnVisibilityModel: {
                  dateToUSigned: false,
                  accepted_terms_version: false
                }
              }
            }}
            showToolbar
          />
        </Paper>
      ) : null}
      {confirmDeleteUserDialog}
      {editUserDialogOpen && renderUserForm}
      <InfoDialog
        isOpen={infoDialogOpen}
        handleClick={() => {
          window.location.reload();
        }}
        icon={<CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />}
        title={<Typography variant="h4">Success </Typography>}
        content={<Typography variant="body1">{infoDialogContent}</Typography>}
      />
    </Box>
  );
};

export default Users;
