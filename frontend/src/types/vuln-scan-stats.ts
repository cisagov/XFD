export interface CVEItem {
  count: number | null;
  cve_string: string | null;
  vuln_name: string | null;
  cvss_base_score: number | null;
  severity_string: string | null;
}

export interface VulnScanSummary {
  id: number;
  summary_date?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  organization?: string | null;
  enrolled_in_vs_timestamp?: string | null;

  asset_count?: number | null;
  assets_owned_count?: number | null;
  false_positive_count?: number | null;
  vulnerable_host_count?: number | null;
  scanned_asset_count?: number | null;

  unique_service_count?: number | null;
  unique_low_severity_count?: number | null;
  unique_medium_severity_count?: number | null;
  unique_high_severity_count?: number | null;
  unique_critical_severity_count?: number | null;

  risky_services_count?: number | null;
  unsupported_software_count?: number | null;
  unique_os_count?: number | null;

  low_severity_count?: number | null;
  medium_severity_count?: number | null;
  high_severity_count?: number | null;
  critical_severity_count?: number | null;

  critical_max_age?: number | null;
  high_max_age?: number | null;
  medium_max_age?: number | null;
  low_max_age?: number | null;

  low_kev_count?: number | null;
  medium_kev_count?: number | null;
  high_kev_count?: number | null;
  critical_kev_count?: number | null;

  kev_max_age?: number | null;
  critical_kev_max_age?: number | null;
  high_kev_max_age?: number | null;
  medium_kev_max_age?: number | null;
  low_kev_max_age?: number | null;

  one_to_five_vulns_count?: number | null;
  six_to_nine_vulns_count?: number | null;
  ten_plus_vulns_count?: number | null;

  top_5_occurring_cves?: CVEItem[] | null;
  top_5_occurring_kevs?: CVEItem[] | null;

  included_tickets?: object[] | null;
  top_5_risky_hosts?:
    | object[]
    | {
        [ip: string]: {
          rrs: number;
          low: number;
          medium: number;
          high: number;
          critical: number;
          total: number;
          domain_id: string;
        } | null;
      };
}

export interface HostSummaries {
  id: number;
  summary_date?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  organization?: string | null;
  host_done_count?: number | null;
  host_waiting_count?: number | null;
  host_running_count?: number | null;
  host_ready_count?: number | null;
  up_host_count?: number | null;
  down_host_count?: number | null;
  scanned_asset_count?: number | null;
}

export interface PortScanSummaries {
  id: number;
  start_date?: string | null;
  end_date?: string | null;
  summary_date?: string | null;
  organization?: string | null;
  open_port_count?: number | null;
  risky_port_count?: number | null;
  nmi_service_count?: number | null;
  unique_ip_count?: number | null;
  unique_service_count?: number | null;
  risky_service_group_counts?: {
    ftp?: number;
    sql?: number;
    netbios?: number;
    ldap?: number;
    rpc?: number;
    irc?: number;
    kerberos?: number;
    rdp?: number;
    telnet?: number;
    smb?: number;
  } | null;
}

export interface PortScanServiceSummaries {
  id: number;
  start_date?: string | null;
  end_date?: string | null;
  summary_date?: string | null;
  organization?: string | null;
  service_name?: string | null;
  open_port_count?: number | null;
  risky_ports?: [] | number[] | null;
  unique_ip_count?: number | null;
  unique_service_count?: number | null;
}

export interface StatsTrendsRawData {
  host_summaries: HostSummaries[];
  port_scan_summaries: PortScanSummaries[];
  port_scan_service_summaries: PortScanServiceSummaries[];
  vuln_scan_summaries: VulnScanSummary[];
}

export interface ServiceData {
  serviceName: string;
  count: number;
}

export interface KeyMetrics {
  title: string;
  value: number;
  hasLink?: boolean;
  startDate?: string;
  endDate?: string;
  dateRange?: string;
}
export interface Top5VulnerableHostsGraphData {
  hostName: string;
  lowSeverity: number;
  mediumSeverity: number;
  highSeverity: number;
  criticalSeverity: number;
  all: number;
  domainId: string;
  rrs?: number;
}
export interface SeverityByProminenceGraphData {
  vulnType: string;
  lowSeverity: number;
  mediumSeverity: number;
  highSeverity: number;
  criticalSeverity: number;
  lowMaxAge?: number;
  mediumMaxAge?: number;
  highMaxAge?: number;
  criticalMaxAge?: number;
}

export interface ScanningSummary {
  hostScan: string;
  vulnerabilityScan: string;
  assetsOwned: number;
  hostsScanned: number;
  startDate?: string;
  endDate: string;
  enrolledDate: string;
  recentlyEnrolled: boolean;
}

export type VulnScanDataTransformed = {
  vulnScanSummary: ScanningSummary[];
  vulnScanKeyMetrics: KeyMetrics[];
  detectedServicesKeyMetrics: KeyMetrics[];
  detectedHostsKeyMetrics: KeyMetrics[];
  detectedHostsTop5VulnerableHosts: Top5VulnerableHostsGraphData[];
  topVulnerabilities: CVEItem[];
  topKevVulnerabilities: CVEItem[];
  riskyServices: ServiceData[];
  severityByProminence: SeverityByProminenceGraphData[];
};
