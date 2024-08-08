import { useState, useEffect, useRef, useCallback } from 'react';

export const useUserActivityTimeout = (timeout: number, loggedIn: boolean) => {
  const [isTimedOut, setIsTimedOut] = useState<boolean>(false);
  const [resetKey, setResetKey] = useState<number>(0);
  const lastActivityTimeRef = useRef<Date>(new Date());

  // This function will be used to reset the timeout externally
  const resetTimeout = useCallback(() => {
    setIsTimedOut(false);
    setResetKey((key) => key + 1);
  }, []);

  const updateLastActivityTime = useCallback(() => {
    lastActivityTimeRef.current = new Date();
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', updateLastActivityTime);
    window.addEventListener('keydown', updateLastActivityTime);

    return () => {
      window.removeEventListener('mousemove', updateLastActivityTime);
      window.removeEventListener('keydown', updateLastActivityTime);
    };
  }, [updateLastActivityTime]);

  useEffect(() => {
    const checkLastActivityTime = () => {
      if (loggedIn) {
        const now = new Date();
        const timeSinceLastActivity =
          now.getTime() - lastActivityTimeRef.current.getTime();
        if (timeSinceLastActivity > timeout) {
          setIsTimedOut(true);
        }
      }
    };

    const intervalId = setInterval(checkLastActivityTime, 1000);

    return () => clearInterval(intervalId);
  }, [timeout, resetKey, loggedIn]);

  return { isTimedOut, resetTimeout };
};