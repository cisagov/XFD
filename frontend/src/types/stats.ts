export interface SummaryStats {
  severity: {
    High: number | null;
    Low: number | null;
    Medium: number | null;
  };
  org: {
    name: string;
    acronym: string;
    root_domains: [];
    ip_blocks: [];
    state_name: string;
    region_id: string;
    members: string;
    rootDomainCount: number;
  };
}

export interface VulnSummaryStats {
  dnstwist_vuln_count: number;
  cred_breach_count: number;
  inventory_count: number;
}
