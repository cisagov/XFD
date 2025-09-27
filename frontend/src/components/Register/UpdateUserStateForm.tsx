import React, { useState } from 'react';
import * as registerFormStyles from './registerFormStyle';
import {
  Button,
  CircularProgress,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Select,
  Typography
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { SelectChangeEvent } from '@mui/material/Select';
import { STATE_OPTIONS } from 'constants/constants';
import { useAuthContext } from 'context';

const StyledDialog = registerFormStyles.StyledDialog;

export interface UpdateStateFormValues {
  state: string;
}

export const UpdateStateForm: React.FC<{
  open: boolean;
  user_id: string;
  onClose: () => void;
}> = ({ open, user_id, onClose }) => {
  const defaultValues = () => ({
    state: ''
  });

  const [values, setValues] = useState<UpdateStateFormValues>(defaultValues);
  const [errorRequestMessage, setErrorRequestMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const { apiPost, apiGet, logout, user } = useAuthContext();

  const handleChange = (event: SelectChangeEvent) => {
    setValues((values: any) => ({
      ...values,
      [event.target.name]: event.target.value
    }));
  };

  const onSave = async () => {
    setIsLoading(true);
    const body = {
      state: values.state
    };

    try {
      await apiPost(`/v2/update_user/${user_id}`, {
        body
      });

      // AFTER successful state update, check maintenance immediately
      const notifications = await apiGet('/notifications');
      const active = notifications.find(
        (n: any) =>
          n.status === 'active' &&
          n.maintenance_type === 'major' &&
          new Date(n.start_datetime) <= new Date() &&
          new Date(n.end_datetime) >= new Date()
      );

      if (active && user?.user_type !== 'globalAdmin') {
        window.dispatchEvent(
          new CustomEvent('maintenance-blocked', {
            detail: { message: active.message }
          })
        );
      }

      setIsLoading(false);
      // Save state selection to local storage to avoid logout re-trigger
      localStorage.setItem('user_state', values.state);
      onClose(); // Only close after handling
    } catch (error) {
      setErrorRequestMessage(
        'Something went wrong updating the state. Please try again.'
      );
      setIsLoading(false);
    }
  };
  return (
    <StyledDialog
      open={open}
      onClose={(event, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
          logout(); // <-- logout if closed without saving to force state
        } else {
          onClose(); // only allow normal onClose otherwise
        }
      }}
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle id="form-dialog-title">Update State Information</DialogTitle>
      <DialogContent>
        {errorRequestMessage && (
          <p className="text-error">{errorRequestMessage}</p>
        )}
        State
        <Select
          displayEmpty
          size="small"
          id="state"
          value={values.state}
          name="state"
          onChange={handleChange}
          fullWidth
          renderValue={
            values.state !== ''
              ? undefined
              : () => <Typography color="#bdbdbd">Select your State</Typography>
          }
        >
          {STATE_OPTIONS.map((state: string, index: number) => (
            <MenuItem key={index} value={state}>
              {state}
            </MenuItem>
          ))}
        </Select>
      </DialogContent>
      <DialogActions>
        <Button
          variant="outlined"
          onClick={logout} // <-- logout when Cancel clicked to force state value
          disabled={user?.invite_pending === true}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={onSave}
          startIcon={
            isLoading ? (
              <CircularProgress color="secondary" size={16} />
            ) : (
              <Save />
            )
          }
        >
          Save
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};
