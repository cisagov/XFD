import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  IconButton,
  Paper,
  Typography,
  Stack,
  Button
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
import { parseISO, format } from 'date-fns';
import UserForm from './UserForm';

type ApiErrorStates = {
  getUsersError: string;
  getAddUserError: string;
  getDeleteError: string;
  getUpdateUserError: string;
};

export interface ApiResponse {
  result: User[];
  count: number;
  url?: string;
}

interface UserType extends User {
  lastLoggedInString?: string | null | undefined;
  dateToUSigned?: string | null | undefined;
  orgs?: string | null | undefined;
  fullName: string;
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
    getUpdateUserError: ''
  });
  const [formValues, setFormValues] = useState<UserFormValues>(
    initialUserFormValues
  );

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const rows = await apiGet<UserType[]>(`/users/`);
      rows.forEach((row) => {
        row.lastLoggedInString = row.lastLoggedIn
          ? format(parseISO(row.lastLoggedIn), 'MM-dd-yyyy hh:mm a')
          : 'None';
        row.dateToUSigned = row.dateAcceptedTerms
          ? format(parseISO(row.dateAcceptedTerms), 'MM-dd-yyyy hh:mm a')
          : 'None';
        row.orgs = row.roles
          ? row.roles
              .filter((role) => role.approved)
              .map((role) => role.organization.name)
              .join(', ')
          : 'None';
        row.fullName = `${row.firstName} ${row.lastName}`;
      });
      if (user?.userType !== 'standard') {
        setUsers(rows);
      } else if (user) {
        setUsers([user]);
      }
      setApiErrorStates((prev) => ({ ...prev, getUsersError: '' }));
    } catch (e: any) {
      setLoadingError(true);
      setApiErrorStates((prev) => ({ ...prev, getUsersError: e.message }));
    } finally {
      setIsLoading(false);
    }
  }, [apiGet, user]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const userCols: GridColDef[] = [
    { field: 'fullName', headerName: 'Name', minWidth: 100, flex: 1 },
    { field: 'email', headerName: 'Email', minWidth: 100, flex: 1.5 },
    { field: 'regionId', headerName: 'Region', minWidth: 100, flex: 0.4 },
    {
      field: 'orgs',
      headerName: 'Organizations',
      minWidth: 100,
      flex: 1
    },
    { field: 'userType', headerName: 'User Type', minWidth: 100, flex: 0.75 },
    {
      field: 'dateToUSigned',
      headerName: 'Date ToU Signed',
      minWidth: 100,
      flex: 1
    },
    {
      field: 'acceptedTermsVersion',
      headerName: 'ToU Version',
      minWidth: 100,
      flex: 0.5
    },
    {
      field: 'lastLoggedInString',
      headerName: 'Last Logged In',
      minWidth: 100,
      flex: 1
    },
    {
      field: 'edit',
      headerName: 'View/Edit',
      minWidth: 50,
      flex: 0.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        const ariaLabel = `View or edit user ${cellValues.row.fullName}`;
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
                  firstName: cellValues.row.firstName,
                  lastName: cellValues.row.lastName,
                  email: cellValues.row.email,
                  userType: cellValues.row.userType,
                  state: cellValues.row.state || '',
                  regionId: cellValues.row.regionId || '',
                  orgName: cellValues.row.roles[0]?.organization?.name || '',
                  orgId: cellValues.row.roles[0]?.organization?.id || ''
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
  if (user?.userType === 'globalAdmin') {
    userCols.push({
      field: 'delete',
      headerName: 'Delete',
      minWidth: 50,
      flex: 0.4,
      renderCell: (cellValues: GridRenderCellParams) => {
        const ariaLabel = `Delete user ${cellValues.row.fullName}`;
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
  const addUserButton = user?.userType === 'globalAdmin' && (
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
            This request will permanently remove <b>{selectedRow?.fullName}</b>{' '}
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

  return (
    <Box display="flex" justifyContent="center">
      <Box
        mb={3}
        mt={3}
        display="flex"
        flexDirection="column"
        sx={{ width: '80%' }}
      >
        <Typography
          fontSize={34}
          fontWeight="medium"
          letterSpacing={0}
          my={3}
          variant="h1"
        >
          Users
        </Typography>
        <Box mb={3} mt={3} display="flex" justifyContent="center">
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
            <Paper elevation={2} sx={{ width: '100%' }}>
              <DataGrid
                rows={users}
                columns={userCols}
                slots={{ toolbar: CustomToolbar }}
                slotProps={{
                  toolbar: { children: addUserButton }
                }}
                initialState={{
                  pagination: { paginationModel: { pageSize: 15 } }
                }}
                pageSizeOptions={[15, 30, 50, 100]}
              />
            </Paper>
          ) : null}
        </Box>
        {confirmDeleteUserDialog}
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
        {user?.userType === 'globalAdmin' && (
          <>
            <ImportExport<
              | User
              | {
                  roles: string;
                }
            >
              name="users"
              fieldsToImport={[
                'firstName',
                'lastName',
                'email',
                'roles',
                'userType',
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
          icon={
            <CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />
          }
          title={<Typography variant="h4">Success </Typography>}
          content={<Typography variant="body1">{infoDialogContent}</Typography>}
        />
      </Box>
    </Box>
  );
};

export default Users;
