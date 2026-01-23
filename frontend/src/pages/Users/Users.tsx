import React, { useCallback, useEffect, useState } from 'react';
import { format } from 'date-fns';
import { useTheme } from '@mui/material/styles';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutline';
import { DataGrid } from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import InfoDialog from 'components/Dialog/InfoDialog';
import { User, UserFormValues } from 'types';
import {
  initializeUser,
  initialUserFormValues
} from '@/constants/userAndOrgData';
import { useAuthContext } from 'context';
import UserForm from './UserForm';
import { ENDPOINTS } from '@/constants/endpoints';
import { logger } from '@/utils/logger';
import { useUserColumns } from './useUserColumns';

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
  org_acronym?: string | null | undefined;
  full_name: string;
  approved_by?: ApprovedBy | null;
  date_approved?: string | null;
}

export const Users: React.FC = () => {
  const { user, apiDelete, apiGet } = useAuthContext();
  const [selectedRow, setSelectedRow] = useState<UserType>(initializeUser);
  const [users, setUsers] = useState<UserType[]>([]);
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
  const theme = useTheme();

  // TODO: Create playwright tests to cover updated Regional Admin access across the application. https://maestro.dhs.gov/jira/browse/CRASM-3183
  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const rows = await apiGet<UserType[]>(ENDPOINTS.USERS);
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
        row.org_acronym = row.roles[0]?.organization.acronym || '';
      });

      const filteredRows = rows;

      setUsers(filteredRows);
      setApiErrorStates((prev) => ({ ...prev, getUsersError: '' }));
    } catch (e: any) {
      setLoadingError(true);
      setApiErrorStates((prev) => ({ ...prev, getUsersError: e.message }));
    } finally {
      setIsLoading(false);
    }
  }, [apiGet]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const userCols = useUserColumns({
    user,
    setSelectedRow,
    setFormValues,
    setEditUserDialogOpen,
    setDeleteUserDialogOpen
  });

  const deleteRow = async (row: UserType) => {
    try {
      await apiDelete(ENDPOINTS.USER.replace('{user_id}', String(row.id)), {
        body: {}
      });
      setUsers(users.filter((user) => user.id !== row.id));
      setApiErrorStates({ ...apiErrorStates, getDeleteError: '' });
      setInfoDialogContent('This user has been successfully removed.');
      setInfoDialogOpen(true);
    } catch (e: any) {
      setApiErrorStates({ ...apiErrorStates, getDeleteError: e.message });
      setInfoDialogContent(
        'This user has been not been removed. Check the console log for more details.'
      );
      logger.error('Users.deleteRow failed:', { error: e, userId: row.id });
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
    px: { xs: 1, sm: 1, md: 1, lg: 1, xl: 0 }
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
                disableExport: true,
                exportTitle: 'Users'
              } as any,
              basePopper: {
                placement: 'bottom-start'
              },
              columnsManagement: {
                getTogglableColumns: (columns) => {
                  const alwaysVisible = ['full_name'];
                  return columns
                    .filter(
                      (col) => col.field && !alwaysVisible.includes(col.field)
                    )
                    .map((col) => col.field as string);
                }
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
            pageSizeOptions={[15, 30, 50, 100]}
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
        icon={
          <CheckCircleOutline
            sx={{ fontSize: '80px', color: theme.palette.primary.dark }}
          />
        }
        title={<Typography variant="h4">Success </Typography>}
        content={<Typography variant="body1">{infoDialogContent}</Typography>}
      />
    </Box>
  );
};

export default Users;
