import { useCallback } from 'react';
import { logger } from '@/utils/logger';
import { toUTC } from 'utils/dateUtils';
import { MaintenanceNotification } from 'types';

interface UseSubmitFormProps {
  formValues: any;
  setFormErrors: (errors: any) => void;
  setActiveNotification: (notification: MaintenanceNotification) => void;
  setInactiveNotifications: React.Dispatch<
    React.SetStateAction<MaintenanceNotification[]>
  >;
  initialNotificationValues: MaintenanceNotification;
  activeNotification: MaintenanceNotification;
  inactiveNotifications: MaintenanceNotification[];
  user: { email?: string };
  handleNotificationAction: (
    body: MaintenanceNotification,
    apiType: string
  ) => Promise<MaintenanceNotification>;
  dateValidator: (start: string, end: string) => [boolean, string];
}

export function useSubmitForm({
  formValues,
  setFormErrors,
  setActiveNotification,
  setInactiveNotifications,
  initialNotificationValues,
  activeNotification,
  inactiveNotifications,
  user,
  handleNotificationAction,
  dateValidator
}: UseSubmitFormProps) {
  return useCallback(
    async (apiType: string) => {
      const invalidDate = dateValidator(
        formValues.start_datetime,
        formValues.end_datetime
      );
      const body: MaintenanceNotification = {
        id: formValues.id,
        maintenance_type: formValues.maintenance_type,
        status: formValues.status,
        updated_by: user?.email || '',
        message: formValues.message,
        start_datetime: toUTC(formValues.start_datetime),
        end_datetime: toUTC(formValues.end_datetime)
      };
      const newFormErrors = {
        maintenance_type: !formValues.maintenance_type,
        message: !formValues.message,
        start_datetime: invalidDate[0],
        end_datetime: invalidDate[0],
        dateMessage: invalidDate[1]
      };
      setFormErrors(newFormErrors);
      if (Object.values(newFormErrors).some((error) => error)) {
        return;
      }
      if (body.status !== 'active') {
        body.status = 'inactive';
      }
      if (apiType === 'update') {
        try {
          const notification = await handleNotificationAction(body, apiType);
          if (body.id === activeNotification.id) {
            if (notification.status === 'active') {
              setActiveNotification({ ...notification });
            } else {
              setActiveNotification(initialNotificationValues);
              setInactiveNotifications([
                ...inactiveNotifications,
                notification
              ]);
            }
          } else {
            if (body.status === 'active') {
              const updatedActiveNotification = {
                ...activeNotification,
                status: 'inactive'
              };
              if (updatedActiveNotification.id !== '1') {
                const formerActiveNotification = await handleNotificationAction(
                  updatedActiveNotification,
                  'update'
                );
                setInactiveNotifications([
                  ...inactiveNotifications.filter(
                    (row: MaintenanceNotification) => row.id !== body.id
                  ),
                  formerActiveNotification as MaintenanceNotification
                ]);
              } else {
                setInactiveNotifications(
                  inactiveNotifications.filter((item) => item.id !== body.id)
                );
              }
              setActiveNotification(body);
            } else {
              setInactiveNotifications(
                (prevInactiveNotifications: MaintenanceNotification[]) => {
                  return prevInactiveNotifications.map(
                    (
                      notification: MaintenanceNotification
                    ): MaintenanceNotification => {
                      if (notification.id === body.id) {
                        return body;
                      } else {
                        return notification;
                      }
                    }
                  );
                }
              );
            }
          }
        } catch (error) {
          logger.error('useNotificationSubmit: Update request failed', {
            error,
            notificationId: body.id
          });
        }
      }
      if (apiType === 'post') {
        try {
          const notification = await handleNotificationAction(body, apiType);
          if (notification.status === 'active') {
            if (activeNotification.status === 'active') {
              const updatedActiveNotification = {
                ...activeNotification,
                status: 'inactive'
              };
              await handleNotificationAction(
                updatedActiveNotification,
                'update'
              );
              setInactiveNotifications([
                ...inactiveNotifications,
                updatedActiveNotification
              ]);
            }
            setActiveNotification(notification);
          } else {
            setInactiveNotifications([...inactiveNotifications, notification]);
          }
        } catch (error) {
          logger.error('useNotificationSubmit: Post request failed', {
            error,
            status: body.status
          });
        }
      }
    },
    [
      formValues,
      setFormErrors,
      setActiveNotification,
      setInactiveNotifications,
      initialNotificationValues,
      activeNotification,
      inactiveNotifications,
      user,
      handleNotificationAction,
      dateValidator
    ]
  );
}
