import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Autocomplete,
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
import { REGION_STATE_MAP, STATE_OPTIONS } from 'constants/constants';
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
  full_name: string;
  date_approved?: string | null | undefined;
  approved_by_id?: string | null | undefined;
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
    first_name: false,
    last_name: false,
    email: false,
    user_type: false,
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
      if (values.region_id) {
        rows = await apiGet<Organization[]>(
          '/organizations/region_id/' + values.region_id
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
  }, [apiGet, values.region_id, setApiErrorStates]);

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
      first_name:
        values.first_name.trim() === '' || !nameRegex.test(values.first_name),
      last_name:
        values.last_name.trim() === '' || !nameRegex.test(values.last_name),
      email: !emailRegex.test(values.email),
      user_type: values.user_type.trim() === '',
      state: values.state.trim() === ''
    };
    setFormErrors(newFormErrors);
    return !Object.values(newFormErrors).some((error) => error);
  };

  const validateField = (name: string, value: string) => {
    const nameRegex = /^[A-Za-z\s-']+$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    switch (name) {
      case 'first_name':
      case 'last_name':
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
      first_name: false,
      last_name: false,
      email: false,
      user_type: false,
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
      first_name: values.first_name,
      last_name: values.last_name,
      email: values.email,
      user_type: values.user_type,
      state: values.state,
      region_id: values.region_id
    };
    try {
      const user = await apiPost('/users', {
        body
      });
      user.full_name = `${user.first_name} ${user.last_name}`;
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
    if (!validateForm(values) || values.org_id === '') {
      return;
    }
    const body = {
      first_name: values.first_name,
      last_name: values.last_name,
      user_type: values.user_type,
      state: values.state,
      region_id: values.region_id
    };
    try {
      await apiPut(`/v2/users/${values.id}`, { body });
      if (values.originalOrgId !== values.org_id) {
        if (values.originalOrgId) {
          await apiPost(
            `/organizations/${values.originalOrgId}/roles/${values.originalRoleId}/remove`,
            { body: {} }
          );
        }
        await apiPost(`/v2/organizations/${values.org_id}/users`, {
          body: { user_id: values.id, role: 'user' }
        });
      }
      const updatedUsers = users.map((user) =>
        user.id === values.id
          ? {
              ...user,
              ...values,
              full_name: `${values.first_name} ${values.last_name}`
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
      region_id: REGION_STATE_MAP[String(event.target.value)],
      org_id: '',
      org_name: ''
    }));
  };

  const handleOrgChange = (newOrgId: string | null) => {
    const orgId = newOrgId ?? '';
    if (values.originalOrgId !== orgId) {
      setInitialOrgIdChange(true);
    } else {
      setInitialOrgIdChange(false);
    }
    setValues((values: any) => ({
      ...values,
      org_id: orgId,
      org_name: getOrgNameById(orgId)
    }));
  };

  const textFieldStyling = {
    '& .MuiOutlinedInput-root': {
      '&.Mui-focused fieldset': {
        borderRadius: '0px'
      }
    }
  };

  const sortedOrgs = organizationsInRegion
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name));

  const formContents = (
    <DialogContent>
      <Grid container spacing={1}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography>First Name</Typography>
          <TextField
            sx={textFieldStyling}
            placeholder="Enter a First Name"
            size="small"
            margin="dense"
            id="first_name"
            slotProps={{
              htmlInput: { maxLength: 250 }
            }}
            name="first_name"
            error={formErrors.first_name}
            helperText={
              formErrors.first_name &&
              'First Name is required and cannot contain numbers'
            }
            type="text"
            fullWidth
            value={values.first_name}
            onChange={onTextChange}
            disabled={user?.user_type !== 'globalAdmin'}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography>Last Name</Typography>
          <TextField
            sx={textFieldStyling}
            placeholder="Enter a Last Name"
            size="small"
            margin="dense"
            id="last_name"
            slotProps={{
              htmlInput: { maxLength: 250 }
            }}
            name="last_name"
            error={formErrors.last_name}
            helperText={
              formErrors.last_name &&
              'Last Name is required and cannot contain numbers'
            }
            type="text"
            fullWidth
            value={values.last_name}
            onChange={onTextChange}
            disabled={user?.user_type !== 'globalAdmin'}
          />
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Typography>Email</Typography>
          <TextField
            sx={textFieldStyling}
            placeholder="Enter an Email"
            size="small"
            margin="dense"
            id="email"
            slotProps={{
              htmlInput: { maxLength: 250 }
            }}
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
        <Grid size={{ xs: 12 }}>
          <Typography mb={1}>State</Typography>
          <Select
            displayEmpty
            size="small"
            id="state"
            value={values.state || ''}
            name="state"
            error={formErrors.state}
            onChange={handleStateChange}
            fullWidth
            MenuProps={{
              anchorOrigin: {
                vertical: 'bottom',
                horizontal: 'left'
              },
              transformOrigin: {
                vertical: 'top',
                horizontal: 'left'
              },
              PaperProps: {
                style: {
                  marginTop: 5,
                  maxHeight: 250,
                  overflowY: 'auto'
                }
              }
            }}
            renderValue={
              values.state !== ''
                ? undefined
                : () => <Typography color="#bdbdbd">Select a State</Typography>
            }
            disabled={user?.user_type !== 'globalAdmin'}
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
        <Grid size={{ xs: 12 }}>
          <Typography mb={1}>Organization</Typography>
          {newUserDialogOpen ? (
            <Alert severity="info">
              An organization cannot be selected until the user is in the
              system.
            </Alert>
          ) : isLoading ? (
            <Alert severity="info">Loading organization selections..</Alert>
          ) : apiErrorStates.getOrgsError ? (
            <Alert severity="info">
              {apiErrorStates.getOrgsError}. An error occurred retrieving
              organizations for this state.
            </Alert>
          ) : values.state === '' ? (
            <Alert severity="info">Select a state to make a selection.</Alert>
          ) : organizationsInRegion.length === 0 ? (
            <Alert severity="info">
              No organizations found. Add orgs to Region {values.region_id} to
              make a selection.
            </Alert>
          ) : (
            <Autocomplete
              size="small"
              id="org_id"
              fullWidth
              disabled={
                organizationsInRegion.length === 0 ||
                user?.user_type !== 'globalAdmin'
              }
              options={sortedOrgs}
              getOptionLabel={(option) => option.name}
              value={sortedOrgs.find((org) => org.id === values.org_id) || null}
              onChange={(_, newValue) => {
                handleOrgChange(newValue ? newValue.id : '');
              }}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              slotProps={{
                listbox: {
                  sx: { maxHeight: 200, overflow: 'auto' }
                }
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  placeholder="Select an Organization"
                  error={values.org_id === ''}
                  helperText={
                    values.org_id === '' ? (
                      <Typography variant="caption" color="error.main">
                        Organization is required
                      </Typography>
                    ) : null
                  }
                />
              )}
            />
          )}
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Typography mt={1}>User Type</Typography>
          <RadioGroup
            aria-label="User Type"
            name="user_type"
            value={values.user_type}
            onChange={onTextChange}
          >
            <FormControlLabel
              value="standard"
              control={<Radio color="primary" />}
              label="Standard"
              disabled={user?.user_type !== 'globalAdmin'}
            />
            <FormControlLabel
              value="globalView"
              control={<Radio color="primary" />}
              label="Global View"
              disabled={user?.user_type !== 'globalAdmin'}
            />
            <FormControlLabel
              value="regionalAdmin"
              control={<Radio color="primary" />}
              label="Regional Administrator"
              disabled={user?.user_type !== 'globalAdmin'}
            />
            <FormControlLabel
              value="globalAdmin"
              control={<Radio color="primary" />}
              label="Global Administrator"
              disabled={user?.user_type !== 'globalAdmin'}
            />
          </RadioGroup>
          {formErrors.user_type && (
            <Typography pl={2} variant="caption" color="error.main">
              User Type is required
            </Typography>
          )}
        </Grid>
        <Grid size={{ xs: 12 }}>
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
        values.org_id === ''
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
