import { MaintenanceNotification } from 'types';

interface UseNotificationActionProps {
  apiPost: (url: string, options: any) => Promise<any>;
  apiDelete: (url: string) => Promise<any>;
  handleApiCall: (
    apiCall: () => Promise<MaintenanceNotification>,
    successMessage: string,
    errorMessage: string
  ) => Promise<MaintenanceNotification>;
}

export function useNotificationAction({
  apiPost,
  apiDelete,
  handleApiCall
}: UseNotificationActionProps) {
  return async (
    body: MaintenanceNotification,
    apiType: string
  ): Promise<MaintenanceNotification> => {
    let notification;
    try {
      if (apiType === 'update') {
        notification = await handleApiCall(
          () => apiPost('/update_notification/' + body.id, { body }),
          'The notification was successfully updated.',
          'The notification was not able to be updated.'
        );
      } else if (apiType === 'post') {
        notification = await handleApiCall(
          () => apiPost('/notifications', { body }),
          'The creation of the new notification was successful.',
          'The creation of the new notification was unsuccessful.'
        );
      } else {
        notification = await handleApiCall(
          () => apiDelete('/notifications/' + body.id),
          'The deletion of the notification was successful.',
          'The deletion of the notification was unsuccessful.'
        );
      }
    } catch (error) {
      console.error('Error occurred during handleNotificationAction:', error);
      throw error;
    }
    return notification;
  };
}
