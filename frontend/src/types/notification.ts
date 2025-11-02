import { format } from 'date-fns';

export interface MaintenanceNotification {
  id: string;
  maintenance_type: string;
  status: string;
  updated_by: string;
  message: string;
  start_datetime: string;
  end_datetime: string;
}

export const initialNotificationValues = {
  id: '1',
  maintenance_type: '',
  status: 'inactive',
  updated_by: '',
  message: '',
  start_datetime: format(new Date(), 'yyyy-MM-dd HH:mm'),
  end_datetime: format(new Date(), 'yyyy-MM-dd HH:mm')
};
