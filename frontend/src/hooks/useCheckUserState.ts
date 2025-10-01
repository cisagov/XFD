import { useEffect, useState } from 'react';

export function useCheckUserState(user: any, isLoggingOut: boolean | null) {
  const [isUpdateStateFormOpen, setIsUpdateStateFormOpen] = useState(false);

  useEffect(() => {
    if (!isLoggingOut && user) {
      if (
        (!user.state || user.state === '') &&
        !localStorage.getItem('user_state')
      ) {
        setIsUpdateStateFormOpen(true);
      }
    }
  }, [user, isLoggingOut]);

  return { isUpdateStateFormOpen, setIsUpdateStateFormOpen };
}
