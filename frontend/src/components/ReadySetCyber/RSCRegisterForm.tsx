import React, { useEffect, useState } from 'react';
import * as RSCregisterFormStyles from './RSCregisterFormStyle';
import {
  Button,
  CircularProgress,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { User } from 'types';

const StyledDialog = RSCregisterFormStyles.StyledDialog;

export interface RegisterFormValues {
  firstName: string;
  lastName: string;
  email: string;
}

export interface ApiResponse {
  result: User;
  count: number;
  url?: string;
}

export const RSCRegisterForm: React.FC<{
  open: boolean;
  onClose: () => void;
  setRegisterSuccess: Function;
}> = ({ open, onClose, setRegisterSuccess }) => {
  // Set default Values
  const defaultValues = () => ({
    firstName: '',
    lastName: '',
    email: ''
  });

  const registerRSCUserPost = async (body: Object) => {
    try {
      const requestOptions: RequestInit = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      };
      const response = await fetch(
        process.env.REACT_APP_API_URL + '/readysetcyber/register',
        requestOptions
      );
      const data = await response.json();
      // Handle the response data here
      console.log(data);
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

  const isDisabled = () => {
    if (Object.values(values).every((value) => value) && !errorEmailMessage) {
      return false;
    } else {
      return true;
    }
  };

  const onSave = async () => {
    setIsLoading(true);
    console.log('values: ', values);
    console.log('This is where we will send the values to post.');
    const body = {
      firstName: values.firstName,
      lastName: values.lastName,
      email: values.email
    };
    const registeredUser = await registerRSCUserPost(body);
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
        Register with RSC Dashboard
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
          inputProps={{ maxLength: 250 }}
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
          id="firstName"
          inputProps={{ maxLength: 250 }}
          name="firstName"
          placeholder="Enter your First Name"
          type="text"
          fullWidth
          value={values.firstName}
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
          id="lastName"
          inputProps={{ maxLength: 250 }}
          name="lastName"
          placeholder="Enter your Last Name"
          type="text"
          fullWidth
          value={values.lastName}
          onChange={onTextChange}
        />
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
