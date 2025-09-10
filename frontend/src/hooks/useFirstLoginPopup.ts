import { useEffect, useRef, useState } from 'react';
import { User } from 'types/user';

export default function useFirstLoginPopup(
  user: User | null,
  apiPut: any,
  apiGet: any,
  setUser: any
) {
  const [show, setShow] = useState(!!user?.first_login);
  const dismissedRef = useRef(false);

  useEffect(() => {
    if (!user || dismissedRef.current) return;
    setShow(!!user.first_login);
  }, [user]);

  const close = async () => {
    dismissedRef.current = true;
    setShow(false);
    try {
      await apiPut(`/v2/users/${user?.id}`, { body: { first_login: false } });
      const refreshed = await apiGet('/users/me');
      setUser?.(refreshed);
    } catch (err) {
      console.error('Failed to update first_login:', err);
    }
  };

  return { show, close };
}
