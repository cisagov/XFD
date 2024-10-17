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
    numVulnerabilities: Point[];
    total: number;
  };
  vulnerabilities: {
    severity: Point[];
    byOrg: Point[];
    latestVulnerabilities: Vulnerability[];
    mostCommonVulnerabilities: VulnerabilityCount[];
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
    rootDomains: [];
    ipBlocks: [];
    stateName: string;
    regionId: string;
    members: string;
    rootDomainCount: number;
  };
}

export interface VulnSummaryStats {
  dnstwist_vuln_count: number;
  cred_breach_count: number;
  inventory_count: number;
}
