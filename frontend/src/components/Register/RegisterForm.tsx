import React, { useEffect, useState } from 'react';
import * as registerFormStyles from './registerFormStyle';
import {
  Button,
  CircularProgress,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Select,
  TextField,
  Typography
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { SelectChangeEvent } from '@mui/material/Select';
import { User } from 'types';
import { STATE_OPTIONS } from 'constants/constants';

const StyledDialog = registerFormStyles.StyledDialog;

export interface RegisterFormValues {
  first_name: string;
  last_name: string;
  email: string;
  state: string;
}

export interface ApiResponse {
  result: User;
  count: number;
  url?: string;
}

export const RegisterForm: React.FC<{
  open: boolean;
  onClose: () => void;
  setRegisterSuccess: Function;
}> = ({ open, onClose, setRegisterSuccess }) => {
  // Set default Values
  const defaultValues = (): RegisterFormValues => ({
    first_name: '',
    last_name: '',
    email: '',
    state: ''
  });

  const registerUserPost = async (body: Object) => {
    try {
      const requestOptions: RequestInit = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      };
      const response = await fetch(
        import.meta.env.VITE_API_URL + '/users/register',
        requestOptions
      );
      const data = await response.json();
      // Handle the response data here
      return data;
    } catch (error) {
      // Handle any errors here
      console.error(error);
    }
  };

  const [values, setValues] = useState<RegisterFormValues>(defaultValues);
  const [errorRequestMessage, setErrorRequestMessage] = useState<string>('');
  const [errorEmailMessage, setEmailErrorMessage] = useState<string>(
    'Email entry error. Please try again.'
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
  > = (e) => onChange(e.target.name, e.target.value);

  const onChange = (name: string, value: any) => {
    setValues((values) => ({
      ...values,
      [name]: value
    }));
  };

  const handleChange = (event: SelectChangeEvent) => {
    setValues((values) => ({
      ...values,
      [event.target.name]: event.target.value
    }));
  };

  const isDisabled = () => {
    if (Object.values(values).every((value) => value) && !errorEmailMessage) {
      return false;
    } else {
      return true;
    }
  };

  const onSave = async () => {
    setIsLoading(true);
    const body = {
      first_name: values.first_name,
      last_name: values.last_name,
      email: values.email,
      state: values.state
    };
    const registeredUser = await registerUserPost(body);
    if (registeredUser !== undefined) {
      console.log('User Registered Successfully');
      setIsLoading(false);
      onClose();
      setRegisterSuccess(true);
    } else {
      console.log('User Register Failed');
      setErrorRequestMessage(
        'Something went wrong registering. Please try again.'
      );
      setIsLoading(false);
    }
  };

  const validateEmail = (email: string) => {
    // email format
    const regexEmail =
      /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/;
    let error = false;
    if (email && regexEmail.test(email)) {
      setEmailErrorMessage('');
      error = false;
    } else {
      setEmailErrorMessage('Email is not valid.');
      error = true;
    }
    return error;
  };

  useEffect(() => {
    if (values && values.email) {
      validateEmail(values.email);
    }
  }, [values]);

  return (
    <StyledDialog
      open={open}
      onClose={() => onClose}
      // aria-labelledby="form-dialog-title"
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle id="form-dialog-title">
        Register with CyHy Dashboard
      </DialogTitle>
      <DialogContent>
        {errorRequestMessage && (
          <p className="text-error">{errorRequestMessage}</p>
        )}
        Email
        <TextField
          sx={{
            '& .MuiOutlinedInput-root': {
              '&.Mui-focused fieldset': {
                borderRadius: '0px'
              }
            }
          }}
          error={errorEmailMessage ? true : false}
          margin="dense"
          size="small"
          id="email"
          slotProps={{ htmlInput: { maxLength: 250 } }}
          name="email"
          placeholder="Enter your Email Address"
          type="text"
          fullWidth
          value={values.email}
          onChange={onTextChange}
          helperText={errorEmailMessage ? errorEmailMessage : null}
          autoFocus
        />
        First Name
        <TextField
          sx={{
            '& .MuiOutlinedInput-root': {
              '&.Mui-focused fieldset': {
                borderRadius: '0px'
              }
            }
          }}
          margin="dense"
          size="small"
          id="first_name"
          slotProps={{ htmlInput: { maxLength: 250 } }}
          name="first_name"
          placeholder="Enter your First Name"
          type="text"
          fullWidth
          value={values.first_name}
          onChange={onTextChange}
        />
        Last Name
        <TextField
          sx={{
            '& .MuiOutlinedInput-root': {
              '&.Mui-focused fieldset': {
                borderRadius: '0px'
              }
            }
          }}
          margin="dense"
          size="small"
          id="last_name"
          slotProps={{ htmlInput: { maxLength: 250 } }}
          name="last_name"
          placeholder="Enter your Last Name"
          type="text"
          fullWidth
          value={values.last_name}
          onChange={onTextChange}
        />
        <Typography my={1}>State</Typography>
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
          disabled={isDisabled()}
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
          Register
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};
