import React, { useCallback, useEffect } from 'react';
import { parse } from 'query-string';
import { useAuthContext } from 'context';
import { User } from 'types';
import { useHistory } from 'react-router-dom';

type OktaCallbackResponse = {
  token: string;
  user: User;
};

export const OktaCallback: React.FC = () => {
  const { apiPost, login } = useAuthContext();
  const history = useHistory();

  const handleOktaCallback = useCallback(async () => {
    const { code } = parse(window.location.search);
    console.log('Code: ', code);
    const nonce = localStorage.getItem('nonce');
    console.log('Nonce: ', nonce);

    try {
      // Pass request to backend callback endpoint
      const response = await apiPost<OktaCallbackResponse>(
        '/auth/okta-callback',
        {
          body: {
            code: code
          }
        }
      );
      console.log('Response: ', response);
      console.log('token ', response.token);

      // Login
      await login(response.token);

      // Storage Management
      localStorage.setItem('token', response.token);
      localStorage.removeItem('nonce');
      localStorage.removeItem('state');

      history.push('/');
    } catch (e) {
      console.error(e);
      history.push('/');
    }
  }, [apiPost, history, login]);

  useEffect(() => {
    handleOktaCallback();
  }, [handleOktaCallback]);

  return <div>Loading...</div>;
};
