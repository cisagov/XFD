import { useEffect, useRef, useState } from 'react';
import { logger } from '@/utils/logger';
import { User } from 'types/user';
import { ENDPOINTS } from '@/constants/endpoints';
import { useUpdateUser } from './useUpdateUser';

export default function useFirstLoginPopup(
  user: User | null,
  apiGet: any,
  setUser: any
) {
  const [show, setShow] = useState(!!user?.first_login);
  const dismissedRef = useRef(false);
  const { updateUser } = useUpdateUser();

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
      await updateUser(userId, { first_login: false });
      const refreshed = await apiGet(ENDPOINTS.USERS_ME);
      setUser?.(refreshed);
    } catch (err) {
      logger.error('useFirstLoginPopup: Failed to update first_login status', {
        error: err,
        userId
      });
    }
  };

  return { show, close };
}
