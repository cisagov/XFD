export interface MaintenanceNotification {
  id?: string;
  maintenanceType: string;
  status: string;
  updatedBy: string;
  message: string;
  startDatetime: string;
  endDatetime: string;
}

export const initialNotificationValues = {
  id: '',
  maintenanceType: '',
  status: '',
  updatedAt: '',
  updatedBy: '',
  message: '',
  startDatetime: '',
  endDatetime: ''
};
