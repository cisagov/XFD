import classes from './Users.module.scss';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Button as MuiButton,
  Dialog as MuiDialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
  Radio,
  RadioGroup,
  Select,
  TextField,
  Typography
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { Add, CheckCircleOutline, Edit, Delete } from '@mui/icons-material';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import InfoDialog from 'components/Dialog/InfoDialog';
import { ImportExport } from 'components';
import { initializeUser, Organization, User } from 'types';
import { useAuthContext } from 'context';
import { STATE_OPTIONS } from '../../constants/constants';
import { formatDistanceToNow, parseISO } from 'date-fns';

type ErrorStates = {
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
}

type UserFormValues = {
  id?: string;
  firstName: string;
  lastName: string;
  email: string;
  organization?: Organization;
  userType: string;
  state: string;
};

const initialUserFormValues = {
  firstName: '',
  lastName: '',
  email: '',
  userType: '',
  state: ''
};

type CloseReason = 'backdropClick' | 'escapeKeyDown' | 'closeButtonClick';

export const Users: React.FC = () => {
  const { user, apiDelete, apiGet, apiPost, apiPut } = useAuthContext();
  const [selectedRow, setSelectedRow] = useState<UserType>(initializeUser);
  const [users, setUsers] = useState<UserType[]>([]);
  const [newUserDialogOpen, setNewUserDialogOpen] = useState(false);
  const [editUserDialogOpen, setEditUserDialogOpen] = useState(false);
  const [deleteUserDialogOpen, setDeleteUserDialogOpen] = useState(false);
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [infoDialogContent, setInfoDialogContent] = useState<string>('');
  const [formDisabled, setFormDisabled] = React.useState(true);
  const [formErrors, setFormErrors] = useState({
    firstName: false,
    lastName: false,
    email: false,
    userType: false,
    state: false
  });
  const [errorStates, setErrorStates] = useState<ErrorStates>({
    getUsersError: '',
    getAddUserError: '',
    getDeleteError: '',
    getUpdateUserError: ''
  });
  const [values, setValues] = useState<UserFormValues>(initialUserFormValues);

  const fetchUsers = useCallback(async () => {
    try {
      const rows = await apiGet<UserType[]>(`/users/`);
      rows.forEach((row) => {
        row.lastLoggedInString = row.lastLoggedIn
          ? `${formatDistanceToNow(parseISO(row.lastLoggedIn))} ago`
          : 'None';
        row.dateToUSigned = row.dateAcceptedTerms
          ? `${formatDistanceToNow(parseISO(row.dateAcceptedTerms))} ago`
          : 'None';
        row.orgs = row.roles
          ? row.roles
              .filter((role) => role.approved)
              .map((role) => role.organization.name)
              .join(', ')
          : 'None';
      });
      if (user?.userType === 'globalAdmin') {
        setUsers(rows);
      } else if (user?.userType === 'regionalAdmin' && user?.regionId) {
        setUsers(rows.filter((row) => row.regionId === user.regionId));
      } else if (user) {
        setUsers([user]);
      }
      setErrorStates((prev) => ({ ...prev, getUsersError: '' }));
    } catch (e: any) {
      setErrorStates((prev) => ({ ...prev, getUsersError: e.message }));
    }
  }, [apiGet, user]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const userCols: GridColDef[] = [
    { field: 'fullName', headerName: 'Name', minWidth: 100, flex: 1 },
    { field: 'email', headerName: 'Email', minWidth: 100, flex: 1.75 },
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
      flex: 0.75
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
      flex: 0.75
    },
    {
      field: 'edit',
      headerName: 'Edit',
      minWidth: 50,
      flex: 0.4,
      renderCell: (cellValues: GridRenderCellParams) => {
        const ariaLabel = `Edit user ${cellValues.row.email}`;
        const descriptionId = `edit-description-${cellValues.row.id}`;
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
                setValues(cellValues.row);
                setEditUserDialogOpen(true);
              }}
            >
              <Edit />
            </IconButton>
          </>
        );
      }
    },
    {
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
    }
  ];

  const addUserButton = user?.userType === 'globalAdmin' && (
    <MuiButton
      size="small"
      sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
      startIcon={<Add />}
      onClick={() => setNewUserDialogOpen(true)}
    >
      Invite New User
    </MuiButton>
  );

  const onResetForm = () => {
    setFormDisabled(false);
    setEditUserDialogOpen(false);
    setNewUserDialogOpen(false);
    setDeleteUserDialogOpen(false);
    setInfoDialogOpen(false);
    setValues(initialUserFormValues);
    setFormErrors({
      firstName: false,
      lastName: false,
      email: false,
      userType: false,
      state: false
    });
  };

  const handleCloseAddUserDialog = (value: CloseReason) => {
    if (value === 'backdropClick' || value === 'escapeKeyDown') {
      return;
    }
    onResetForm();
  };

  const deleteRow = async (row: UserType) => {
    try {
      await apiDelete(`/users/${row.id}`, { body: {} });
      setUsers(users.filter((user) => user.id !== row.id));
      setErrorStates({ ...errorStates, getDeleteError: '' });
      setInfoDialogContent('This user has been successfully removed.');
      setInfoDialogOpen(true);
    } catch (e: any) {
      setErrorStates({ ...errorStates, getDeleteError: e.message });
      setInfoDialogContent(
        'This user has been not been removed. Check the console log for more details.'
      );
      console.log(e);
    }
  };

  const onCreateUserSubmit = async (e: any) => {
    e.preventDefault();
    const body = {
      firstName: values.firstName,
      lastName: values.lastName,
      email: values.email,
      userType: values.userType,
      state: values.state
    };
    const { firstName, lastName, email, userType, state } = values;
    const newFormErrors = {
      firstName: !firstName,
      lastName: !lastName,
      email: !email,
      userType: !userType,
      state: !state
    };
    setFormErrors(newFormErrors);
    if (Object.values(newFormErrors).some((error) => error)) {
      return;
    }
    try {
      const user = await apiPost('/users/', {
        body
      });
      setUsers(users.concat(user));
      setErrorStates({ ...errorStates, getAddUserError: '' });
      handleCloseAddUserDialog('closeButtonClick');
      setInfoDialogContent('This user has been successfully added.');
      setInfoDialogOpen(true);
    } catch (e: any) {
      setErrorStates({ ...errorStates, getAddUserError: e.message });
      setInfoDialogContent(
        'This user has been not been added. Check the console log for more details.'
      );
      console.log(e);
      setValues(initialUserFormValues);
    }
  };

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
  > = (e) => onChange(e.target.name, e.target.value);

  const onChange = (name: string, value: any) => {
    setValues((values) => ({
      ...values,
      [name]: value
    }));
    setFormDisabled(false);
  };

  const handleChange = (event: SelectChangeEvent) => {
    setValues((values) => ({
      ...values,
      [event.target.name]: event.target.value
    }));
  };

  const textFieldStyling = {
    '& .MuiOutlinedInput-root': {
      '&.Mui-focused fieldset': {
        borderRadius: '0px'
      }
    }
  };

  const updateRow = async (row: UserFormValues) => {
    try {
      await apiPut(`/v2/users/${row.id}`, { body: { userType: row.userType } });
      const updateUsers = (prevUsers: any[]) =>
        prevUsers.map((user) => {
          if (user.id === row.id) {
            return { ...user, userType: row.userType };
          }
          return user;
        });
      setUsers(updateUsers(users));
      setErrorStates({ ...errorStates, getUpdateUserError: '' });
      setInfoDialogContent('This user has been successfully updated.');
      setInfoDialogOpen(true);
    } catch (e: any) {
      setErrorStates({ ...errorStates, getUpdateUserError: e.message });
      setInfoDialogContent(
        'This user has been not been updated. Check the console log for more details.'
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
      onCancel={onResetForm}
      title={'Are you sure you want to delete this user?'}
      content={
        <>
          <Typography mb={3}>
            This request will permanently remove <b>{selectedRow?.fullName}</b>{' '}
            from Crossfeed and cannot be undone.
          </Typography>
          {errorStates.getDeleteError && (
            <Alert severity="error">
              Error removing user: {errorStates.getDeleteError}. See the network
              tab for more details.
            </Alert>
          )}
        </>
      }
      screenWidth="xs"
    />
  );

  const formContents = (
    <DialogContent>
      <Typography mt={1}>First Name</Typography>
      <TextField
        sx={textFieldStyling}
        placeholder="Enter a First Name"
        size="small"
        margin="dense"
        id="firstName"
        inputProps={{ maxLength: 250 }}
        name="firstName"
        error={formErrors.firstName}
        helperText={formErrors.firstName && 'First Name is required'}
        type="text"
        fullWidth
        value={values.firstName}
        onChange={onTextChange}
        disabled={editUserDialogOpen}
      />
      <Typography mt={1}>Last Name</Typography>
      <TextField
        sx={textFieldStyling}
        placeholder="Enter a Last Name"
        size="small"
        margin="dense"
        id="lastName"
        inputProps={{ maxLength: 250 }}
        name="lastName"
        error={formErrors.lastName}
        helperText={formErrors.lastName && 'Last Name is required'}
        type="text"
        fullWidth
        value={values.lastName}
        onChange={onTextChange}
        disabled={editUserDialogOpen}
      />
      <Typography mt={1}>Email</Typography>
      <TextField
        sx={textFieldStyling}
        placeholder="Enter an Email"
        size="small"
        margin="dense"
        id="email"
        inputProps={{ maxLength: 250 }}
        name="email"
        error={formErrors.email}
        helperText={formErrors.email && 'Email is required'}
        type="text"
        fullWidth
        value={values.email}
        onChange={onTextChange}
        disabled={editUserDialogOpen}
      />
      <Typography mt={1}>State</Typography>
      <Select
        displayEmpty
        size="small"
        id="state"
        value={values.state === null ? '' : values.state}
        name="state"
        error={formErrors.state}
        onChange={handleChange}
        fullWidth
        renderValue={
          values.state !== ''
            ? undefined
            : () => <Typography color="#bdbdbd">Select a State</Typography>
        }
        disabled={editUserDialogOpen}
      >
        {STATE_OPTIONS.map((state: string, index: number) => (
          <MenuItem key={index} value={state}>
            {state}
          </MenuItem>
        ))}
      </Select>
      {formErrors.state && (
        <Typography pl={2} variant="caption" color="error.main">
          State is required
        </Typography>
      )}
      <Typography mt={2}>User Type</Typography>
      <RadioGroup
        aria-label="User Type"
        name="userType"
        value={values.userType}
        onChange={onTextChange}
      >
        <FormControlLabel
          value="standard"
          control={<Radio color="primary" />}
          label="Standard"
        />
        <FormControlLabel
          value="globalView"
          control={<Radio color="primary" />}
          label="Global View"
        />
        <FormControlLabel
          value="regionalAdmin"
          control={<Radio color="primary" />}
          label="Regional Administrator"
        />
        <FormControlLabel
          value="globalAdmin"
          control={<Radio color="primary" />}
          label="Global Administrator"
        />
      </RadioGroup>
      {formErrors.userType && (
        <Typography pl={2} variant="caption" color="error.main">
          User Type is required
        </Typography>
      )}
      {errorStates.getAddUserError && (
        <Alert severity="error">
          Error adding user to the database: {errorStates.getAddUserError}. See
          the network tab for more details.
        </Alert>
      )}
    </DialogContent>
  );

  const confirmEditNotificationDialog = (
    <ConfirmDialog
      isOpen={editUserDialogOpen}
      onConfirm={() => updateRow(values)}
      onCancel={onResetForm}
      title={'Update User'}
      content={formContents}
      disabled={formDisabled}
    />
  );

  return (
    <div className={classes.root}>
      <h1>Users</h1>
      <Paper elevation={0}>
        <DataGrid
          rows={users}
          columns={userCols}
          slots={{ toolbar: CustomToolbar }}
          slotProps={{
            toolbar: { children: addUserButton }
          }}
        />
      </Paper>
      {confirmDeleteUserDialog}
      <MuiDialog
        open={newUserDialogOpen}
        onClose={(_, reason) => handleCloseAddUserDialog(reason)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Invite a User</DialogTitle>
        {formContents}
        <DialogActions>
          <MuiButton
            variant="outlined"
            onClick={() => {
              setNewUserDialogOpen(false);
              setFormErrors({
                firstName: false,
                lastName: false,
                email: false,
                userType: false,
                state: false
              });
              setValues(initialUserFormValues);
            }}
          >
            Cancel
          </MuiButton>
          <MuiButton
            variant="contained"
            type="submit"
            onClick={onCreateUserSubmit}
          >
            Invite User
          </MuiButton>
        </DialogActions>
      </MuiDialog>
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
      {confirmEditNotificationDialog}
      <InfoDialog
        isOpen={infoDialogOpen}
        handleClick={() => {
          onResetForm();
          window.location.reload();
        }}
        icon={<CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />}
        title={<Typography variant="h4">Success </Typography>}
        content={<Typography variant="body1">{infoDialogContent}</Typography>}
      />
    </div>
  );
};

export default Users;
