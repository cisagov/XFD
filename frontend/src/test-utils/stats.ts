import { SummaryStats, VulnSummaryStats } from 'types';

export const summaryData: SummaryStats = {
  severity: { High: 5, Medium: 10, Low: 15 },
  org: {
    name: 'Name of Org',
    acronym: 'TEST',
    rootDomains: [],
    ipBlocks: [],
    stateName: 'Name of State',
    regionId: '1',
    members: '10',
    rootDomainCount: 10
  }
};

export const vulnSummaryData: VulnSummaryStats = {
  dnstwist_vuln_count: 10,
  cred_breach_count: 10,
  inventory_count: 10
};

export const wasFindingsData = {
  scanDate: '5 Jul 2024',
  activeVulns: '10',
  newVulns: '10',
  reopenedVulns: '10',
  sensitiveContent: '10'
};
