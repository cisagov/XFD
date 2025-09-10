import { Vulnerability } from './domain';
import { GridFilterItem } from '@mui/x-data-grid';

export interface ApiResponse {
  result: Vulnerability[];
  count: number;
  url?: string;
}

export const stateMap: { [key: string]: string } = {
  unconfirmed: 'Unconfirmed',
  exploitable: 'Exploitable',
  'false-positive': 'False Positive',
  'accepted-risk': 'Accepted Risk',
  remediated: 'Remediated'
};

interface LooseVulnerabilityRow {
  id: string;
  title: string;
  severity: string;
  is_kev: string;
  is_kev_ransomware: string;
  domain: string | undefined;
  domainId: string | undefined;
  product: string;
  created_at: string;
  state: string;
}

type Nullable<T> = {
  [P in keyof T]: T[P] | null;
};

export type VulnerabilityRow = Nullable<LooseVulnerabilityRow>;

export interface LocationState {
  domain?: any;
  severity?: string;
  title?: string;
  kev?: boolean;
  orgName?: string;
  orgId?: string;
  startDate?: string;
  endDate?: string;
  dateRange?: string;
  scanType?: string;
}

export type SearchParams = {
  filters: GridFilterItem[];
  page: number;
  pageSize?: number;
  doExport?: boolean;
  order?: string;
  sort?: 'asc' | 'desc';
  group_by?: string;
  showAll?: boolean;
  is_kev?: boolean;
  organization?: string;
};
