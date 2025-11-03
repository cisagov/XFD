import React, { useState } from 'react';
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { SelectChangeEvent } from '@mui/material/Select';
import { STATE_OPTIONS } from '@/constants/constants';
import { useAuthContext } from 'context';

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

      localStorage.setItem('user_state', values.state);

      try {
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
      } catch (notificationError) {
        console.warn(
          'Failed to check maintenance notifications:',
          notificationError
        );
      }

      setIsLoading(false);
      onClose(); // Only close after handling
    } catch (error) {
      setErrorRequestMessage(
        'Something went wrong updating the state. Please try again.'
      );
      setIsLoading(false);
    }
  };
  return (
    <Dialog
      open={open}
      onClose={(event: any, reason: string) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
          logout(); // <-- logout if closed without saving to force state
        } else {
          onClose(); // only allow normal onClose otherwise
        }
      }}
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle id="form-dialog-title" sx={{ pb: 1 }}>
        Update State Information
      </DialogTitle>
      <DialogContent sx={{ pt: 1 }}>
        {errorRequestMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorRequestMessage}
          </Alert>
        )}
        <FormControl fullWidth size="small" sx={{ mt: 1 }}>
          <InputLabel id="state-select-label">Select Your State</InputLabel>
          <Select
            labelId="state-select-label"
            id="state"
            value={values.state}
            name="state"
            label="State"
            onChange={handleChange}
            displayEmpty={false}
          >
            {STATE_OPTIONS.map((state: string, index: number) => (
              <MenuItem key={index} value={state}>
                {state}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions sx={{ p: 2, pt: 1 }}>
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
    </Dialog>
  );
};
