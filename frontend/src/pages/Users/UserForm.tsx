import React, { useState } from 'react';
import {
  Alert,
  DialogContent,
  FormControlLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  TextField,
  Typography
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import { initialUserFormValues, User, UserFormValues } from 'types';
import { useAuthContext } from 'context';
import { STATE_OPTIONS } from '../../constants/constants';

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
  const { user, apiPost, apiPut } = useAuthContext();
  const [formDisabled, setFormDisabled] = useState(true);
  const [formErrors, setFormErrors] = useState({
    firstName: false,
    lastName: false,
    email: false,
    userType: false,
    state: false
  });

  const validateForm = (values: UserFormValues) => {
    const nameRegex = /^[A-Za-z\s]+$/;
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
    const nameRegex = /^[A-Za-z\s]+$/;
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

  const isFormValid = () => {
    return (
      !Object.values(formErrors).some((error) => error) &&
      Object.values(values)
        .filter((value) => typeof value === 'string')
        .every((value) => (value as string).trim() !== '')
    );
  };

  const onResetForm = () => {
    console.log('formDisabled: ', formDisabled);
    setFormDisabled(false);
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
    const body: UserFormValues = {
      firstName: values.firstName,
      lastName: values.lastName,
      email: values.email,
      userType: values.userType,
      state: values.state,
      regionId: values.regionId,
      orgName: values.orgName,
      orgId: values.orgId
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
    if (!validateForm(values)) {
      return;
    }
    const body: UserFormValues = {
      firstName: values.firstName,
      lastName: values.lastName,
      email: values.email,
      userType: values.userType,
      state: values.state,
      regionId: values.regionId,
      orgName: values.orgName,
      orgId: values.orgId
    };
    try {
      await apiPut(`/v2/users/${values.id}`, { body });
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
    setFormDisabled(!isFormValid());
  };

  const onChange = (name: string, value: any) => {
    setValues((values: any) => ({
      ...values,
      [name]: value
    }));
    setFormDisabled(false);
  };

  const handleChange = (event: SelectChangeEvent) => {
    setValues((values: any) => ({
      ...values,
      [event.target.name]: event.target.value
    }));
    setFormDisabled(!isFormValid());
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
        helperText={
          formErrors.firstName &&
          'First Name is required and cannot contain numbers'
        }
        type="text"
        fullWidth
        value={values.firstName}
        onChange={onTextChange}
        disabled={!(user?.userType === 'globalAdmin')}
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
        helperText={
          formErrors.lastName &&
          'Last Name is required and cannot contain numbers'
        }
        type="text"
        fullWidth
        value={values.lastName}
        onChange={onTextChange}
        disabled={!(user?.userType === 'globalAdmin')}
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
        disabled={!(user?.userType === 'globalAdmin')}
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
      {apiErrorStates.getAddUserError && (
        <Alert severity="error">
          Error adding user to the database: {apiErrorStates.getAddUserError}.
          See the network tab for more details.
        </Alert>
      )}
    </DialogContent>
  );

  const editUserFormDialog = (
    <ConfirmDialog
      isOpen={editUserDialogOpen}
      onConfirm={handleEditUserSubmit}
      onCancel={onResetForm}
      title={'Update User'}
      content={formContents}
      disabled={!isFormValid()}
    />
  );

  const inviteUserFormDialog = (
    <ConfirmDialog
      isOpen={newUserDialogOpen}
      onConfirm={onCreateUserSubmit}
      onCancel={() => {
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
      onClose={(_, reason) => handleCloseAddUserDialog(reason)}
      title={'Invite a User'}
      content={formContents}
      disabled={!isFormValid()}
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
