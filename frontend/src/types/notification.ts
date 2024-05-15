import { format } from 'date-fns';

export interface MaintenanceNotification {
  id: string;
  maintenanceType: string;
  status: string;
  updatedBy: string;
  message: string;
  startDatetime: string;
  endDatetime: string;
}

export const initialNotificationValues = {
  id: '1',
  maintenanceType: '',
  status: 'inactive',
  updatedBy: '',
  message: '',
  startDatetime: format(new Date(), 'yyyy-MM-dd HH:mm'),
  endDatetime: format(new Date(), 'yyyy-MM-dd HH:mm')
};
