import { GridFilterItem } from '@mui/x-data-grid';

export interface CustomGridFilterItem<T> extends GridFilterItem {
  customProperty?: T;
}

export interface Query<T extends object> {
  page: number;
  filters: CustomGridFilterItem<T>[];
  // TODO: CRASM-2708: Update /vulnerabilities/search call to pass page_size instead of pageSize
  pageSize?: number;
  page_size?: number;
  showAll?: boolean;
}
