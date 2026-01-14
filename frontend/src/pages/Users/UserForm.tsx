import React, { useEffect, useRef, useState } from 'react';
import { isEqual } from 'lodash';
import Alert from '@mui/material/Alert';
import Autocomplete from '@mui/material/Autocomplete';
import Button from '@mui/material/Button';
import DialogContent from '@mui/material/DialogContent';
import FormControlLabel from '@mui/material/FormControlLabel';
import Grid from '@mui/material/Grid';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import AnimatedConfirmDialog from 'components/Dialog/AnimatedConfirmDialog';
import { Organization, User, UserFormValues } from 'types';
import { initialUserFormValues } from '@/constants/userAndOrgData';
import { useAuthContext } from 'context';
import { REGION_STATE_MAP, STATE_OPTIONS } from '@/constants/constants';
import { logger } from '@/utils/logger';

import { useOrganizationsByRegion } from '@/hooks/useOrganizationsByRegion';
import { useUpdateUser } from '@/hooks/useUpdateUser';
import { useAddUserToOrganization } from '@/hooks/useAddUserToOrganization';
import { useRemoveUserFromOrganization } from '@/hooks/useRemoveUserFromOrganization';

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

type ApiBody = {
  first_name?: string;
  last_name?: string;
  user_type?: string;
  email?: string;
  state: string;
  region_id: string;
};

type UserFormProps = {
  users: UserType[];
  setUsers: Function;
  values: UserFormValues;
  setValues: Function;
  editUserDialogOpen: boolean;
  setEditUserDialogOpen: Function;
  apiErrorStates: ApiErrorStates;
  setApiErrorStates: Function;
  setInfoDialogOpen: Function;
  setInfoDialogContent: Function;
};

const USER_TYPE_MAP = {
  standard: 0,
  globalView: 1,
  regionalAdmin: 2,
  globalAdmin: 3
};

type ElevationControlProps = {
  confirmGlobalAdminChange: string;
  setConfirmGlobalAdminChange: React.Dispatch<React.SetStateAction<string>>;
  userRoleChanged: boolean;
  values: UserFormValues;
  isRoleElevationConfirmed: boolean;
  setIsRoleElevationConfirmed: React.Dispatch<React.SetStateAction<boolean>>;
  userOrg?: string | null;
};

const getAllowedDomains = (): string[] => {
  const raw = import.meta.env.VITE_ALLOWED_ADMIN_EMAIL_DOMAINS;

  if (!raw) return [];

  if (raw.trim() === '*') return ['*'];

  if (raw.trim().startsWith('[')) {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed.map((domain) => domain.trim()).filter(Boolean);
      }
      return [];
    } catch (err) {
      logger.warn(
        'UserForm: Invalid JSON for VITE_ALLOWED_ADMIN_EMAIL_DOMAINS',
        { error: err, raw }
      );
    }
  }

  return raw
    .split(',')
    .map((domain: string) => domain.trim())
    .filter(Boolean);
};

const allowedDomains = getAllowedDomains();

const allowingAllDomains =
  Array.isArray(allowedDomains) &&
  allowedDomains.length === 1 &&
  allowedDomains[0] === '*';

const isPermittedEmail = (email: string): boolean => {
  if (allowingAllDomains) return true;
  const atIndex = email.lastIndexOf('@');
  if (atIndex === -1) return false;

  const domain = email.slice(atIndex + 1).toLowerCase();

  return allowedDomains.some((allowedDomain: string) => {
    const candidate = allowedDomain.toLowerCase();
    return domain === candidate;
  });
};

const ElevationControl: React.FC<ElevationControlProps> = ({
  confirmGlobalAdminChange,
  setConfirmGlobalAdminChange,
  userRoleChanged,
  values,
  isRoleElevationConfirmed,
  setIsRoleElevationConfirmed,
  userOrg
}) => {
  const textFieldStyling = {
    '& .MuiOutlinedInput-root': {
      '&.Mui-focused fieldset': {
        borderRadius: '0px'
      }
    }
  };
  if (!userRoleChanged || values.user_type === 'standard') return <></>;
  if (values.user_type === 'globalAdmin') {
    return (
      <>
        <Alert severity="warning">
          You are attempting to change user{' '}
          <strong>
            {userOrg ? `${values.email} - ${userOrg}` : values.email}
          </strong>{' '}
          to a Global Administrator. This will give them access to all
          organizations and data in the system. Please type{' '}
          <strong>Global Administrator</strong> in the field below to confirm
          this change.
        </Alert>
        <TextField
          sx={textFieldStyling}
          placeholder="Enter Global Administrator to confirm"
          size="small"
          margin="dense"
          id="first_name"
          slotProps={{
            htmlInput: { maxLength: 250 }
          }}
          name="first_name"
          type="text"
          fullWidth
          value={confirmGlobalAdminChange}
          onChange={(event) => setConfirmGlobalAdminChange(event.target.value)}
        />
      </>
    );
  }
  if (values.user_type === 'regionalAdmin' || values.user_type === 'globalView')
    return (
      <>
        <Alert severity={isRoleElevationConfirmed ? 'success' : 'warning'}>
          You are attempting to change this user to{' '}
          <strong>
            {values.user_type === 'regionalAdmin'
              ? 'Regional Administrator'
              : 'Global View'}
          </strong>
          . This will give them access to more organizations and data in the
          system.
          <br />
          <Button
            sx={{ mt: 1 }}
            size="small"
            variant="contained"
            onClick={() => setIsRoleElevationConfirmed(true)}
            disabled={isRoleElevationConfirmed}
          >
            {isRoleElevationConfirmed
              ? 'Confirmed Privilege Elevation'
              : 'Confirm Privilege Elevation'}
          </Button>
        </Alert>
      </>
    );

  return <></>;
};

export const UserForm: React.FC<UserFormProps> = ({
  users,
  setUsers,
  values,
  setValues,
  editUserDialogOpen,
  setEditUserDialogOpen,
  apiErrorStates,
  setApiErrorStates,
  setInfoDialogOpen,
  setInfoDialogContent
}) => {
  const initialValuesRef = useRef(values);
  const { user } = useAuthContext();

  const [formErrors, setFormErrors] = useState({
    first_name: false,
    last_name: false,
    email: false,
    user_type: false,
    state: false
  });
  const [initialOrgIdChange, setInitialOrgIdChange] = useState(false);
  const [confirmGlobalAdminChange, setConfirmGlobalAdminChange] = useState('');
  const [isRoleElevationConfirmed, setIsRoleElevationConfirmed] =
    useState(false);

  const {
    organizations: organizationsInRegion,
    isLoading,
    errorMessage: getOrgsErrorMessage
  } = useOrganizationsByRegion(values.region_id);

  useEffect(() => {
    setApiErrorStates((previousState: ApiErrorStates) => ({
      ...previousState,
      getOrgsError: getOrgsErrorMessage
    }));
  }, [getOrgsErrorMessage, setApiErrorStates]);

  const { updateUser } = useUpdateUser();
  const { addUserToOrganization } = useAddUserToOrganization();
  const { removeUserFromOrganization } = useRemoveUserFromOrganization();

  const getOrgNameById = (id: string) => {
    const organization = organizationsInRegion.find(
      (org: Organization) => org.id === id
    );
    return organization ? organization.name : null;
  };

  const validateForm = (currentValues: UserFormValues) => {
    const nameRegex = /^[A-Za-z\s-']+$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const newFormErrors = {
      first_name:
        currentValues.first_name.trim() === '' ||
        !nameRegex.test(currentValues.first_name),
      last_name:
        currentValues.last_name.trim() === '' ||
        !nameRegex.test(currentValues.last_name),
      email: !emailRegex.test(currentValues.email),
      user_type: currentValues.user_type.trim() === '',
      state: currentValues.state.trim() === ''
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

  const handleEditUserSubmit = async () => {
    if (!validateForm(values) || values.org_id === '') {
      return;
    }

    const userId = values.id;
    if (!userId) {
      logger.error('UserForm.handleEditUserSubmit: missing user id', {
        values
      });
      return;
    }

    const oldRoleLevel =
      USER_TYPE_MAP[user?.user_type as keyof typeof USER_TYPE_MAP] ?? 0;
    const newRoleLevel =
      USER_TYPE_MAP[values?.user_type as keyof typeof USER_TYPE_MAP] ?? 0;

    if (newRoleLevel > oldRoleLevel) {
      logger.info(
        'UserForm: User role elevation detected, confirming with user',
        { oldRole: user?.user_type, newRole: values?.user_type }
      );
    }

    const body: ApiBody = {
      first_name: values.first_name,
      last_name: values.last_name,
      state: values.state,
      region_id: values.region_id
    };

    if (user?.user_type === 'globalAdmin') {
      body.user_type = values.user_type;
    }

    try {
      await updateUser(userId, body);

      if (values.originalOrgId !== values.org_id) {
        if (values.originalOrgId && values.originalRoleId) {
          await removeUserFromOrganization(
            values.originalOrgId,
            values.originalRoleId
          );
        }

        if (values.org_id) {
          await addUserToOrganization(values.org_id, userId, 'user');
        } else {
          logger.error(
            'UserForm.handleEditUserSubmit: org_id missing when attempting to add user to organization',
            { values }
          );
        }
      }

      const updatedUsers = users.map((existingUser: UserType) =>
        existingUser.id === userId
          ? {
              ...existingUser,
              ...values,
              full_name: `${values.first_name} ${values.last_name}`
            }
          : existingUser
      ) as UserType[];

      setUsers(updatedUsers);
      setApiErrorStates({
        ...apiErrorStates,
        getUpdateUserError: ''
      });
      setEditUserDialogOpen(false);
      setInfoDialogContent('This user has been successfully updated.');
      setInfoDialogOpen(true);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      setApiErrorStates({
        ...apiErrorStates,
        getUpdateUserError: error.message + (detail ? `. ${detail}` : '')
      });
      setInfoDialogContent(
        'This user has not been updated. Check the console log for more details.'
      );
      setInfoDialogOpen(true);
      logger.error('UserForm.handleEditUserSubmit failed:', {
        error,
        userId: user?.id
      });
    }
  };

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
  > = (event) => {
    const { name, value } = event.target;
    onChange(name, value);
    const fieldError = validateField(name, value);
    setFormErrors((previousErrors) => ({
      ...previousErrors,
      [name]: fieldError
    }));
  };

  const onChange = (name: string, value: unknown) => {
    setValues((previousValues: any) => ({
      ...previousValues,
      [name]: value
    }));
  };

  const handleOrgChange = (newOrgId: string | null) => {
    const orgId = newOrgId ?? '';
    if (values.originalOrgId !== orgId) {
      setInitialOrgIdChange(true);
    } else {
      setInitialOrgIdChange(false);
    }
    setValues((previousValues: any) => ({
      ...previousValues,
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
    .sort((a: Organization, b: Organization) => a.name.localeCompare(b.name));

  const editedUser = users.find(
    (userItem: UserType) => userItem.id === values.id
  );
  const editedUserOrganization =
    editedUser?.roles[0]?.organization?.name || null;
  const userRoleChanged = editedUser?.user_type !== values.user_type;

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
          <Autocomplete
            id="state"
            size="small"
            options={STATE_OPTIONS}
            disabled={!['globalAdmin'].includes(user?.user_type || '')}
            value={values.state || null}
            onChange={(_, newValue) => {
              setValues((previousValues: any) => ({
                ...previousValues,
                state: newValue || '',
                region_id: newValue ? REGION_STATE_MAP[String(newValue)] : '',
                org_id: '',
                org_name: ''
              }));
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="State"
                error={formErrors.state}
                helperText={
                  formErrors.state ? (
                    <Typography variant="caption" color="error.main">
                      State is required
                    </Typography>
                  ) : null
                }
                disabled={
                  !['globalAdmin', 'regionalAdmin'].includes(
                    user?.user_type || ''
                  )
                }
              />
            )}
            isOptionEqualToValue={(option, value) => option === value}
          />
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Typography mb={1}>Organization</Typography>
          {isLoading ? (
            <Alert severity="info">Loading organization selections..</Alert>
          ) : apiErrorStates.getOrgsError ? (
            <Alert severity="info">
              {apiErrorStates.getOrgsError}. See the network tab for more
              details.
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
              options={sortedOrgs}
              getOptionLabel={(option: Organization) => {
                if (option.name && option.acronym) {
                  return `${option.name} (${option.acronym})`;
                }
                return option.name;
              }}
              value={
                sortedOrgs.find(
                  (organization: Organization) =>
                    organization.id === values.org_id
                ) || null
              }
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
            onChange={(event) => {
              setIsRoleElevationConfirmed(false);
              onTextChange(event);
            }}
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
            {isPermittedEmail(values.email) && (
              <>
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
              </>
            )}
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
      <ElevationControl
        confirmGlobalAdminChange={confirmGlobalAdminChange}
        setConfirmGlobalAdminChange={setConfirmGlobalAdminChange}
        userRoleChanged={userRoleChanged}
        values={values}
        isRoleElevationConfirmed={isRoleElevationConfirmed}
        setIsRoleElevationConfirmed={setIsRoleElevationConfirmed}
        userOrg={editedUserOrganization}
      />
    </DialogContent>
  );

  const isNewGlobalAdmin =
    users?.find((userItem: UserType) => userItem.id === values.id)
      ?.user_type !== values.user_type && values.user_type === 'globalAdmin';

  const isNewRegionalOrGlobalView =
    users?.find((userItem: UserType) => userItem.id === values.id)
      ?.user_type !== values.user_type &&
    (values.user_type === 'regionalAdmin' || values.user_type === 'globalView');

  const editUserFormDialog = (
    <AnimatedConfirmDialog
      isOpen={editUserDialogOpen}
      onConfirm={handleEditUserSubmit}
      onCancel={onResetForm}
      title={'View/Edit User'}
      animateSize={true}
      content={formContents}
      disabled={
        (isEqual(initialValuesRef.current, values) && !initialOrgIdChange) ||
        values.org_id === '' ||
        (isNewGlobalAdmin &&
          confirmGlobalAdminChange !== 'Global Administrator') ||
        (isNewRegionalOrGlobalView && !isRoleElevationConfirmed)
      }
    />
  );

  return <>{editUserFormDialog}</>;
};

export default UserForm;
