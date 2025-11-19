import React, { useState } from 'react';
import { logger } from '@/utils/logger';
import { ErrorOutline } from '@mui/icons-material';
import { MaintenanceNotification } from 'types';

export function useNotificationApiCall(
  setInfoDialogValues: (values: any) => void,
  setInfoDialogToggle: (open: boolean) => void
) {
  return async (
    apiCall: () => Promise<MaintenanceNotification>,
    successMessage: string,
    errorMessage: string
  ) => {
    try {
      const notification = await apiCall();
      setInfoDialogValues((prevState: any) => ({
        ...prevState,
        content: successMessage
      }));
      setInfoDialogToggle(true);
      return notification;
    } catch (e: any) {
      logger.error('useNotificationApiCall: API call failed', {
        error: e,
        successMessage,
        errorMessage
      });
      setInfoDialogValues({
        icon: React.createElement(ErrorOutline, {
          color: 'error',
          'aria-label':
            'an error icon that displays an outlined circle with a x in the center',
          sx: { fontSize: '80px' }
        }),
        title: 'Error',
        content: `${errorMessage} ${e.message}. Check the console log for more details.`
      });
      setInfoDialogToggle(true);
      throw e;
    }
  };
}
