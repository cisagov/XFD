import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import { useAuthContext } from 'context';
import { Button, TextInput, Label } from '@trussworks/react-uswds';

interface FormData {
  email: string;
}
interface Errors extends Partial<FormData> {
  global?: string;
}

export const EmailUnsubscribe: React.FC = () => {
  const history = useHistory();
  const [errors, setErrors] = useState<Errors>({});
  const { apiPost } = useAuthContext();
  const [value, setValue] = useState<FormData>({
    email: ''
  });

  const onTextChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    setValue({
      ...value,
      [e.target.name]: e.target.value
    });
  };

  const onSubmit: React.FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault();
    try {
      if (!value) throw Error('Email must be provided.');
      await apiPost(`/email-unsubscribe`, {
        body: value
      });

      history.push('/unsubscribe', {
        message: 'You have been successfully unsubscribed from our emails.'
      });
    } catch (e: any) {
      setErrors({
        global: e.message ?? e.toString()
      });
    }
  };

  const handleResubscribe = async () => {
    try {
      if (!value) throw Error('Email must be provided.');
      await apiPost(`/email-resubscribe`, {
        body: value
      });

      history.push('/unsubscribe', {
        message: 'You have been successfully resubscribed to our emails.'
      });
    } catch (e: any) {
      setErrors({
        global: e.message ?? e.toString()
      });
    }
  };

  return (
    <form onSubmit={onSubmit}>
      <h1>Unsubscribe from our emails.</h1>
      <p>Youllll no longer receive emails from us.</p>
      <Label htmlFor="email">Email</Label>
      <TextInput
        required
        id="email"
        name="email"
        type="text"
        value={value.email}
        onChange={onTextChange}
      />
      <p></p>
      <div className="width-full display-flex flex-justify-start">
        {errors.global && <p className="text-error">{errors.global}</p>}
      </div>
      <Button type="submit">Unsubscribe</Button>
      <p>Changed your mind?</p>
      <div className="width-full display-flex flex-justify-start">
        {errors.global && <p className="text-error">{errors.global}</p>}
      </div>
      <Button type="button" onClick={handleResubscribe}>
        Resubscribe
      </Button>
    </form>
  );
};
