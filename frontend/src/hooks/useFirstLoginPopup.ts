import { useEffect, useRef, useState } from 'react';
import { User } from 'types/user';
import { ENDPOINTS } from '@/constants/endpoints';

export default function useFirstLoginPopup(
  user: User | null,
  apiPost: any,
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
    const userId = user?.id;
    if (!userId) return;
    try {
      await apiPost(ENDPOINTS.USER_UPDATE_V2.replace('{user_id}', userId), {
        body: { first_login: false }
      });
      const refreshed = await apiGet(ENDPOINTS.USERS_ME);
      setUser?.(refreshed);
    } catch (err) {
      console.error('Failed to update first_login:', err);
    }
  };

  return { show, close };
}
