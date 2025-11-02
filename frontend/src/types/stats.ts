import { Vulnerability } from './domain';

export interface Point {
  id: string;
  label: string;
  value: number;
}

export interface VulnerabilityCount extends Vulnerability {
  count: number;
}

export interface Stats {
  domains: {
    services: Point[];
    ports: Point[];
    num_vulnerabilities: Point[];
    total: number;
  };
  vulnerabilities: {
    severity: Point[];
    by_org: Point[];
    latest_vulnerabilities: Vulnerability[];
    most_common_vulnerabilities: VulnerabilityCount[];
  };
}

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
