import { useEffect, useState } from 'react';

export function useMaintenanceNotifications(
  user: any,
  apiGet: (url: string) => Promise<any>,
  userMustSign: boolean
) {
  const [isLoginBlockedDialogOpen, setIsLoginBlockedDialogOpen] =
    useState(false);
  const [maintenanceNotification, setMaintenanceNotification] =
    useState<any>(null);

  useEffect(() => {
    const fetchAndCheckMaintenance = async () => {
      if (
        user &&
        !user.invite_pending &&
        user.state &&
        user.date_accepted_terms &&
        !isLoginBlockedDialogOpen
      ) {
        const notifications = await apiGet('/notifications');
        const active = notifications.find(
          (n: any) =>
            n.status === 'active' &&
            n.maintenance_type === 'major' &&
            new Date(n.start_datetime) <= new Date() &&
            new Date(n.end_datetime) >= new Date()
        );
        const nonBlockingUserTypes = ['globalAdmin', 'regionalAdmin'];
        if (active && !nonBlockingUserTypes.includes(user.user_type)) {
          setMaintenanceNotification(active);
          setIsLoginBlockedDialogOpen(true);
        }
      }
    };

    fetchAndCheckMaintenance();
  }, [apiGet, isLoginBlockedDialogOpen, user, userMustSign]);

  useEffect(() => {
    const handleMaintenanceBlocked = (e: any) => {
      if (e.detail?.message) {
        setMaintenanceNotification({ message: e.detail.message });
        setIsLoginBlockedDialogOpen(true);
      }
    };

    window.addEventListener('maintenance-blocked', handleMaintenanceBlocked);
    return () => {
      window.removeEventListener(
        'maintenance-blocked',
        handleMaintenanceBlocked
      );
    };
  }, []);

  return {
    isLoginBlockedDialogOpen,
    setIsLoginBlockedDialogOpen,
    maintenanceNotification,
    setMaintenanceNotification
  };
}
