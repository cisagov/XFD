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
import { STATE_OPTIONS } from '../../constants/constants';
import { useAuthContext } from 'context';

const StyledDialog = registerFormStyles.StyledDialog;

export interface UpdateStateFormValues {
  state: string;
}

export const UpdateStateForm: React.FC<{
  open: boolean;
  userId: string;
  onClose: () => void;
}> = ({ open, userId, onClose }) => {
  const defaultValues = () => ({
    state: ''
  });

  const [values, setValues] = useState<UpdateStateFormValues>(defaultValues);
  const [errorRequestMessage, setErrorRequestMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const { apiPut } = useAuthContext();

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
      await apiPut(`/v2/users/${userId}`, {
        body
      });
      setIsLoading(false);
      onClose();
    } catch (error) {
      setErrorRequestMessage(
        'Something went wrong updating the state. Please try again.'
      );
      setIsLoading(false);
    }
  };

  return (
    <StyledDialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
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
        <Button variant="outlined" onClick={onClose}>
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
