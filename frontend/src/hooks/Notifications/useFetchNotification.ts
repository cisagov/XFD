import { useCallback } from 'react';
import { MaintenanceNotification } from 'types';

export function useFetchNotification(
  apiGet: (url: string) => Promise<any>,
  setActiveNotification: (notification: MaintenanceNotification) => void,
  setInactiveNotifications: React.Dispatch<
    React.SetStateAction<MaintenanceNotification[]>
  >,
  initialNotificationValues: MaintenanceNotification
) {
  return useCallback(async () => {
    try {
      const rows = await apiGet('/notifications');
      let activeRow;
      const inactiveRows: MaintenanceNotification[] = [];
      for (const row of rows) {
        if (row.status === 'active') {
          activeRow = { ...row };
        } else {
          inactiveRows.push({ ...row });
        }
      }
      if (activeRow) {
        setActiveNotification(activeRow);
      } else {
        setActiveNotification(initialNotificationValues);
      }
      if (inactiveRows.length > 0) {
        setInactiveNotifications(inactiveRows);
      }
    } catch (e: any) {
      console.log(e);
    }
  }, [
    apiGet,
    setActiveNotification,
    setInactiveNotifications,
    initialNotificationValues
  ]);
}
