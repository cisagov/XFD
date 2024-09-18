import React, { useCallback, useEffect } from 'react';
import { parse } from 'query-string';
import { useAuthContext } from 'context';
import { useHistory } from 'react-router-dom';

type OktaCallbackResponse = any;

export const OktaCallback: React.FC = () => {
  const { apiPost, login } = useAuthContext();
  const history = useHistory();

  const handleOktaCallback = useCallback(async () => {
    const { code } = parse(window.location.search);
    console.log('Code: ', code);

    try {
      // Pass request to backend callback endpoint
      const response = await apiPost<OktaCallbackResponse>(
        '/auth/okta-callback',
        {
          body: {
            code: code
          },
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      console.log('Response: ', response.body);
      console.log('token ', response.body.token);
      const nonce = localStorage.getItem('nonce');
      console.log('Nonce: ', nonce);
      // Login
      login(response.token);
      // Storage Management
      localStorage.setItem('token', response.body.token);
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
