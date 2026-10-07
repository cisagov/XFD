import React from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import { User, UserFormValues } from 'types';

type ElevationControlProps = {
  confirmGlobalAdminChange: string;
  setConfirmGlobalAdminChange: React.Dispatch<React.SetStateAction<string>>;
  userRoleChanged: boolean;
  values: UserFormValues | User;
  isRoleElevationConfirmed: boolean;
  setIsRoleElevationConfirmed: React.Dispatch<React.SetStateAction<boolean>>;
  userOrg?: string | null;
};

export const ElevationControl: React.FC<ElevationControlProps> = ({
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

  if (
    values.user_type === 'globalAdmin' &&
    confirmGlobalAdminChange === 'Global Administrator'
  ) {
    setIsRoleElevationConfirmed(true);
  }

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
          onChange={(event) => {
            setConfirmGlobalAdminChange(event.target.value);
          }}
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
