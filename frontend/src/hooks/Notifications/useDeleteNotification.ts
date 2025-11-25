import { MaintenanceNotification } from 'types';
import { logger } from '@/utils/logger';

interface UseDeleteNotificationProps {
  rowToDelete: MaintenanceNotification;
  setActiveNotification: (notification: MaintenanceNotification) => void;
  setInactiveNotifications: React.Dispatch<
    React.SetStateAction<MaintenanceNotification[]>
  >;
  initialNotificationValues: MaintenanceNotification;
  inactiveNotifications: MaintenanceNotification[];
  handleNotificationAction: (
    body: MaintenanceNotification,
    apiType: string
  ) => Promise<any>;
}

export function useDeleteNotification({
  rowToDelete,
  setActiveNotification,
  setInactiveNotifications,
  initialNotificationValues,
  inactiveNotifications,
  handleNotificationAction
}: UseDeleteNotificationProps) {
  return async () => {
    try {
      await handleNotificationAction(rowToDelete, 'delete');
      if (rowToDelete.status === 'active') {
        setActiveNotification(initialNotificationValues);
      } else {
        setInactiveNotifications(
          inactiveNotifications.filter((item) => item.id !== rowToDelete.id)
        );
      }
    } catch (error) {
      logger.error('useDeleteNotification: Delete failed', {
        error,
        notificationId: rowToDelete.id,
        status: rowToDelete.status
      });
    }
  };
}
