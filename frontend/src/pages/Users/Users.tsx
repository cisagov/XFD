import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  IconButton,
  Paper,
  Typography,
  Stack,
  Button,
  Tooltip
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import {
  Add,
  CheckCircleOutline,
  EditNoteOutlined,
  Delete
} from '@mui/icons-material';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import InfoDialog from 'components/Dialog/InfoDialog';
import { ImportExport } from 'components';
import {
  initialUserFormValues,
  initializeUser,
  User,
  UserFormValues
} from 'types';
import { useAuthContext } from 'context';
import { format } from 'date-fns';
import UserForm from './UserForm';

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
interface ApprovedBy {
  id: string;
  full_name: string;
  first_name: string;
  last_name: string;
  email: string;
  user_type: string;
  region_id: string;
  state: string;
}

interface UserType extends User {
  lastLoggedInString?: string | null | undefined;
  dateToUSigned?: string | null | undefined;
  orgs?: string | null | undefined;
  full_name: string;
  approved_by?: ApprovedBy | null;
  date_approved?: string | null;
}

export const Users: React.FC = () => {
  const { user, apiDelete, apiGet, apiPost } = useAuthContext();
  const [selectedRow, setSelectedRow] = useState<UserType>(initializeUser);
  const [users, setUsers] = useState<UserType[]>([]);
  const [newUserDialogOpen, setNewUserDialogOpen] = useState(false);
  const [editUserDialogOpen, setEditUserDialogOpen] = useState(false);
  const [deleteUserDialogOpen, setDeleteUserDialogOpen] = useState(false);
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [infoDialogContent, setInfoDialogContent] = useState<string>('');
  const [loadingError, setLoadingError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
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

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const rows = await apiGet<UserType[]>(`/users`);
      rows.forEach((row) => {
        row.lastLoggedInString = row.last_logged_in
          ? format(new Date(row.last_logged_in), 'MM-dd-yyyy hh:mm a')
          : 'None';
        row.dateToUSigned = row.date_accepted_terms
          ? format(new Date(row.date_accepted_terms), 'MM-dd-yyyy hh:mm a')
          : 'None';
        row.orgs = row.roles
          ? row.roles
              .filter((role) => role.approved)
              .map((role) => role.organization.name)
              .join(', ')
          : 'None';
        row.full_name = `${row.first_name} ${row.last_name}`;
      });

      let filteredRows = rows;
      if (user?.user_type === 'regionalAdmin' && user.region_id) {
        filteredRows = rows.filter((row) => row.region_id === user.region_id);
      }

      setUsers(filteredRows);
      setApiErrorStates((prev) => ({ ...prev, getUsersError: '' }));
    } catch (e: any) {
      setLoadingError(true);
      setApiErrorStates((prev) => ({ ...prev, getUsersError: e.message }));
    } finally {
      setIsLoading(false);
    }
  }, [apiGet, user?.user_type, user?.region_id]);

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
  const addUserButton = user?.user_type === 'globalAdmin' && (
    <Button
      size="small"
      sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
      startIcon={<Add />}
      onClick={() => setNewUserDialogOpen(true)}
    >
      Invite New User
    </Button>
  );

  const deleteRow = async (row: UserType) => {
    try {
      await apiDelete(`/users/${row.id}`, { body: {} });
      setUsers(users.filter((user) => user.id !== row.id));
      setApiErrorStates({ ...apiErrorStates, getDeleteError: '' });
      setInfoDialogContent('This user has been successfully removed.');
      setInfoDialogOpen(true);
    } catch (e: any) {
      setApiErrorStates({ ...apiErrorStates, getDeleteError: e.message });
      setInfoDialogContent(
        'This user has been not been removed. Check the console log for more details.'
      );
      console.log(e);
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
      newUserDialogOpen={newUserDialogOpen}
      setNewUserDialogOpen={setNewUserDialogOpen}
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
                children: addUserButton,
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
      {(newUserDialogOpen || editUserDialogOpen) && renderUserForm}
      {user?.user_type === 'globalAdmin' && (
        <>
          <ImportExport<
            | User
            | {
                roles: string;
              }
          >
            name="users"
            fieldsToImport={[
              'first_name',
              'last_name',
              'email',
              'roles',
              'user_type',
              'state'
            ]}
            onImport={async (results) => {
              const createdUsers = [];
              for (const result of results) {
                const parsedRoles: {
                  organization: string;
                  role: string;
                }[] = JSON.parse(result.roles as string);
                const body: any = result;
                if (parsedRoles.length > 0) {
                  body.organization = parsedRoles[0].organization;
                  body.organizationAdmin = parsedRoles[0].role === 'admin';
                }
                try {
                  createdUsers.push(
                    await apiPost('/users', {
                      body
                    })
                  );
                } catch (e) {
                  console.error(e);
                }
              }
              setUsers(users.concat(...createdUsers));
            }}
          />
        </>
      )}
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
