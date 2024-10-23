import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  DialogContent,
  FormControlLabel,
  Grid,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  TextField,
  Typography
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import {
  initialUserFormValues,
  Organization,
  User,
  UserFormValues
} from 'types';
import { useAuthContext } from 'context';
import { REGION_STATE_MAP, STATE_OPTIONS } from '../../constants/constants';
import { isEqual } from 'lodash';

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

interface UserType extends User {
  lastLoggedInString?: string | null | undefined;
  dateToUSigned?: string | null | undefined;
  orgs?: string | null | undefined;
  fullName: string;
}

type CloseReason = 'backdropClick' | 'escapeKeyDown' | 'closeButtonClick';

type UserFormProps = {
  users: UserType[];
  setUsers: Function;
  values: UserFormValues;
  setValues: Function;
  newUserDialogOpen: boolean;
  setNewUserDialogOpen: Function;
  editUserDialogOpen: boolean;
  setEditUserDialogOpen: Function;
  apiErrorStates: ApiErrorStates;
  setApiErrorStates: Function;
  setInfoDialogOpen: Function;
  setInfoDialogContent: Function;
};

export const UserForm: React.FC<UserFormProps> = ({
  users,
  setUsers,
  values,
  setValues,
  newUserDialogOpen,
  setNewUserDialogOpen,
  editUserDialogOpen,
  setEditUserDialogOpen,
  apiErrorStates,
  setApiErrorStates,
  setInfoDialogOpen,
  setInfoDialogContent
}) => {
  const initialValuesRef = useRef(values);
  const { user, apiGet, apiPost, apiPut } = useAuthContext();
  const [formErrors, setFormErrors] = useState({
    firstName: false,
    lastName: false,
    email: false,
    userType: false,
    state: false
  });
  const [organizationsInRegion, setOrganizationsInRegion] = useState<
    Organization[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const [initialOrgIdChange, setInitialOrgIdChange] = useState(false);
  const fetchOrganizations = useCallback(async () => {
    setIsLoading(true);
    try {
      let rows: Organization[] = [];
      if (values.regionId) {
        rows = await apiGet<Organization[]>(
          '/organizations/regionId/' + values.regionId
        );
      }
      setOrganizationsInRegion(rows);
      setApiErrorStates((prev: any) => ({ ...prev, getOrgsError: '' }));
    } catch (e: any) {
      setApiErrorStates((prev: any) => ({ ...prev, getOrgsError: e.message }));
      console.log(e);
    } finally {
      setIsLoading(false);
    }
  }, [apiGet, values.regionId, setApiErrorStates]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  const getOrgNameById = (id: string) => {
    const organization = organizationsInRegion.find((org) => org.id === id);
    return organization ? organization.name : null;
  };

  const validateForm = (values: UserFormValues) => {
    const nameRegex = /^[A-Za-z\s-']+$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const newFormErrors = {
      firstName:
        values.firstName.trim() === '' || !nameRegex.test(values.firstName),
      lastName:
        values.lastName.trim() === '' || !nameRegex.test(values.lastName),
      email: !emailRegex.test(values.email),
      userType: values.userType.trim() === '',
      state: values.state.trim() === ''
    };
    setFormErrors(newFormErrors);
    return !Object.values(newFormErrors).some((error) => error);
  };

  const validateField = (name: string, value: string) => {
    const nameRegex = /^[A-Za-z\s-']+$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    switch (name) {
      case 'firstName':
      case 'lastName':
        return value.trim() === '' || !nameRegex.test(value);
      case 'email':
        return !emailRegex.test(value);
      default:
        return value.trim() === '';
    }
  };

  const onResetForm = () => {
    setEditUserDialogOpen(false);
    setNewUserDialogOpen(false);
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

  const onCreateUserSubmit = async () => {
    if (!validateForm(values)) {
      return;
    }
    const body = {
      firstName: values.firstName,
      lastName: values.lastName,
      email: values.email,
      userType: values.userType,
      state: values.state,
      regionId: values.regionId
    };
    try {
      const user = await apiPost('/users/', {
        body
      });
      user.fullName = `${user.firstName} ${user.lastName}`;
      setUsers(users.concat(user));
      setApiErrorStates({ ...apiErrorStates, getAddUserError: '' });
      handleCloseAddUserDialog('closeButtonClick');
      setInfoDialogContent('This user has been successfully invited.');
      setInfoDialogOpen(true);
    } catch (e: any) {
      setApiErrorStates({ ...apiErrorStates, getAddUserError: e.message });
      setInfoDialogContent(
        'This user has been not been invited. Check the console log for more details.'
      );
      console.log(e);
      setValues(initialUserFormValues);
    }
  };

  const handleEditUserSubmit = async () => {
    if (!validateForm(values) || values.orgId === '') {
      return;
    }
    const body = {
      firstName: values.firstName,
      lastName: values.lastName,
      email: values.email,
      userType: values.userType,
      state: values.state,
      regionId: values.regionId
    };
    try {
      await apiPut(`/v2/users/${values.id}`, { body });
      if (values.originalOrgId !== values.orgId) {
        if (values.originalOrgId) {
          await apiPost(
            `/organizations/${values.originalOrgId}/roles/${values.originalRoleId}/remove`,
            { body: {} }
          );
        }
        await apiPost(`/v2/organizations/${values.orgId}/users`, {
          body: { userId: values.id, role: 'user' }
        });
      }
      const updatedUsers = users.map((user) =>
        user.id === values.id
          ? {
              ...user,
              ...values,
              fullName: `${values.firstName} ${values.lastName}`
            }
          : user
      ) as UserType[];
      setUsers(updatedUsers);
      setApiErrorStates({ ...apiErrorStates, getUpdateUserError: '' });
      setEditUserDialogOpen(false);
      setInfoDialogContent('This user has been successfully updated.');
      setInfoDialogOpen(true);
    } catch (e: any) {
      setApiErrorStates({ ...apiErrorStates, getUpdateUserError: e.message });
      setInfoDialogContent(
        'This user has not been updated. Check the console log for more details.'
      );
      console.log(e);
    }
  };

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
  > = (e) => {
    const { name, value } = e.target;
    onChange(name, value);
    const fieldError = validateField(name, value);
    setFormErrors((prevErrors) => ({
      ...prevErrors,
      [name]: fieldError
    }));
  };

  const onChange = (name: string, value: any) => {
    setValues((values: any) => ({
      ...values,
      [name]: value
    }));
  };

  const handleStateChange = (event: SelectChangeEvent) => {
    setValues((values: any) => ({
      ...values,
      [event.target.name]: event.target.value,
      regionId: REGION_STATE_MAP[String(event.target.value)],
      orgId: '',
      orgName: ''
    }));
  };

  const handleOrgChange = (event: SelectChangeEvent) => {
    if (values.originalOrgId !== event.target.value) {
      setInitialOrgIdChange(true);
    } else {
      setInitialOrgIdChange(false);
    }
    setValues((values: any) => ({
      ...values,
      orgId: event.target.value,
      orgName: getOrgNameById(event.target.value)
    }));
  };

  const textFieldStyling = {
    '& .MuiOutlinedInput-root': {
      '&.Mui-focused fieldset': {
        borderRadius: '0px'
      }
    }
  };

  const formContents = (
    <DialogContent>
      <Grid container spacing={1}>
        <Grid item xs={12} md={6}>
          <Typography>First Name</Typography>
          <TextField
            sx={textFieldStyling}
            placeholder="Enter a First Name"
            size="small"
            margin="dense"
            id="firstName"
            inputProps={{ maxLength: 250 }}
            name="firstName"
            error={formErrors.firstName}
            helperText={
              formErrors.firstName &&
              'First Name is required and cannot contain numbers'
            }
            type="text"
            fullWidth
            value={values.firstName}
            onChange={onTextChange}
            disabled={user?.userType !== 'globalAdmin'}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <Typography>Last Name</Typography>
          <TextField
            sx={textFieldStyling}
            placeholder="Enter a Last Name"
            size="small"
            margin="dense"
            id="lastName"
            inputProps={{ maxLength: 250 }}
            name="lastName"
            error={formErrors.lastName}
            helperText={
              formErrors.lastName &&
              'Last Name is required and cannot contain numbers'
            }
            type="text"
            fullWidth
            value={values.lastName}
            onChange={onTextChange}
            disabled={user?.userType !== 'globalAdmin'}
          />
        </Grid>
        <Grid item xs={12}>
          <Typography>Email</Typography>
          <TextField
            sx={textFieldStyling}
            placeholder="Enter an Email"
            size="small"
            margin="dense"
            id="email"
            inputProps={{ maxLength: 250 }}
            name="email"
            error={formErrors.email}
            helperText={
              formErrors.email &&
              'Email is required and must be in the correct format'
            }
            type="text"
            fullWidth
            value={values.email}
            onChange={onTextChange}
            disabled={editUserDialogOpen}
          />
        </Grid>
        <Grid item xs={12}>
          <Typography>State</Typography>
          <Select
            displayEmpty
            size="small"
            id="state"
            value={values.state === null ? '' : values.state}
            name="state"
            error={formErrors.state}
            onChange={handleStateChange}
            fullWidth
            renderValue={
              values.state !== ''
                ? undefined
                : () => <Typography color="#bdbdbd">Select a State</Typography>
            }
            disabled={user?.userType !== 'globalAdmin'}
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
        </Grid>
        <Grid item xs={12}>
          <Typography>Organization</Typography>
          {newUserDialogOpen ? (
            <Alert severity="info">
              An organization cannot be selected until the user is in the
              system.
            </Alert>
          ) : isLoading ? (
            <Alert severity="info">Loading organization selections..</Alert>
          ) : apiErrorStates.getOrgsError ? (
            <Alert severity="info">
              {apiErrorStates.getOrgsError}. Error retrieving organizations.
            </Alert>
          ) : values.state === '' ? (
            <Alert severity="info">Select a state to make a selection.</Alert>
          ) : organizationsInRegion.length === 0 ? (
            <Alert severity="info">
              No organizations found. Add orgs to Region {values.regionId} to
              make a selection.
            </Alert>
          ) : (
            <>
              <Select
                displayEmpty
                size="small"
                id="orgId"
                value={values.orgId === null ? '' : values.orgId}
                name="orgId"
                error={values.orgId === ''}
                onChange={handleOrgChange}
                fullWidth
                renderValue={
                  values.orgId !== ''
                    ? undefined
                    : () => (
                        <Typography color="#bdbdbd">
                          Select an Organization
                        </Typography>
                      )
                }
                disabled={
                  organizationsInRegion.length === 0 ||
                  user?.userType !== 'globalAdmin'
                }
              >
                {organizationsInRegion
                  .sort((a, b) => a.name.localeCompare(b.name))
                  .map((organization) => (
                    <MenuItem key={organization.id} value={organization.id}>
                      {organization.name}
                    </MenuItem>
                  ))}
              </Select>
              {values.orgId === '' && (
                <Typography pl={2} variant="caption" color="error.main">
                  Organization is required
                </Typography>
              )}
            </>
          )}
        </Grid>
        <Grid item xs={12}>
          <Typography mt={1}>User Type</Typography>
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
              disabled={user?.userType !== 'globalAdmin'}
            />
            <FormControlLabel
              value="globalView"
              control={<Radio color="primary" />}
              label="Global View"
              disabled={user?.userType !== 'globalAdmin'}
            />
            <FormControlLabel
              value="regionalAdmin"
              control={<Radio color="primary" />}
              label="Regional Administrator"
              disabled={user?.userType !== 'globalAdmin'}
            />
            <FormControlLabel
              value="globalAdmin"
              control={<Radio color="primary" />}
              label="Global Administrator"
              disabled={user?.userType !== 'globalAdmin'}
            />
          </RadioGroup>
          {formErrors.userType && (
            <Typography pl={2} variant="caption" color="error.main">
              User Type is required
            </Typography>
          )}
        </Grid>
        <Grid item xs={12}>
          {apiErrorStates.getAddUserError && (
            <Alert severity="error">
              Error adding user to the database:{' '}
              {apiErrorStates.getAddUserError}. See the network tab for more
              details.
            </Alert>
          )}
          {apiErrorStates.getUpdateUserError && (
            <Alert severity="error">
              Error updating user in the database:{' '}
              {apiErrorStates.getUpdateUserError}. See the network tab for more
              details.
            </Alert>
          )}
        </Grid>
      </Grid>
    </DialogContent>
  );

  const editUserFormDialog = (
    <ConfirmDialog
      isOpen={editUserDialogOpen}
      onConfirm={handleEditUserSubmit}
      onCancel={onResetForm}
      title={'View/Edit User'}
      content={formContents}
      disabled={
        (isEqual(initialValuesRef.current, values) && !initialOrgIdChange) ||
        values.orgId === ''
      }
    />
  );

  const inviteUserFormDialog = (
    <ConfirmDialog
      isOpen={newUserDialogOpen}
      onConfirm={onCreateUserSubmit}
      onCancel={onResetForm}
      onClose={(_, reason) => handleCloseAddUserDialog(reason)}
      title={'Invite a User'}
      content={formContents}
    />
  );
  return (
    <>
      {inviteUserFormDialog}
      {editUserFormDialog}
    </>
  );
};

export default UserForm;
