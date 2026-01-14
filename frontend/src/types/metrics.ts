export interface OrgCountByStatus {
  http_status: number;
  org_count: number;
}

export interface ScanSummary {
  total_orgs: number;
  id: string;
  name: string;
  org_counts_by_status: OrgCountByStatus[];
}

export interface ScanSummaries {
  scans: ScanSummary[];
  metrics_window_days: number;
}

export interface DailyCount {
  date: string;
  count: number;
}

export interface DailyStatusCount {
  http_status: number;
  daily_counts: DailyCount[];
}

export interface ScanDetails {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  frequency: number;
  last_run: string | null;
  total_orgs: number;
  daily_status_counts: DailyStatusCount[];
  metrics_window_days: number;
}
