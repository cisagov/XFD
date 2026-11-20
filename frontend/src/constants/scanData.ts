import { Scan } from '@/types';

export const getDefaultScanValues = (name: string): Scan => ({
  id: '',
  name,
  arguments: { start_datetime: '', end_datetime: '' },
  frequency: 1,
  frequencyUnit: 'day',
  last_run: '',
  is_granular: false,
  is_user_modifiable: false,
  is_single_scan: false,
  organizations: [],
  concurrent_tasks: 1,
  useDateRange: false,
  startDate: '',
  endDate: '',
  tags: []
});
