import { GridFilterItem } from '@mui/x-data-grid';

export interface CustomGridFilterItem<T> extends GridFilterItem {
  customProperty?: T;
}

export interface Query<T extends object> {
  page: number;
  filters: CustomGridFilterItem<T>[];
  pageSize?: number;
}
