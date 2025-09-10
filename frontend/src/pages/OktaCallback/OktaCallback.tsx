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
  const { login } = useAuthContext();
  const history = useHistory();

  const handleOktaCallback = useCallback(async () => {
    const { code, state } = parse(window.location.search);

    if (!code || !state) {
      console.error('Missing OAuth parameters');
      history.replace('/');
      return;
    }

    const signedToken = localStorage.getItem('oauthMeta');

    if (!signedToken) {
      console.error('Missing signed OAuth metadata');
      history.replace('/');
      return;
    }

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/auth/okta-callback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ code, state, signedToken })
        }
      );

      const data: OktaCallbackResponse & { detail?: string } = await res.json();
      if (!res.ok) throw new Error(data?.detail || 'OAuth callback failed');

      await login(data.token);

      // Clean up
      localStorage.setItem('token', data.token);
      localStorage.removeItem('oauthMeta');
      localStorage.removeItem('nonce');
      localStorage.removeItem('state');

      history.replace('/');
    } catch (e) {
      console.error(e);
      history.replace('/');
    }
  }, [history, login]);

  useEffect(() => {
    handleOktaCallback();
  }, [handleOktaCallback]);

  return <div>Loading...</div>;
};
