import { VulnScanDataTransformed } from '@/types/vuln-scan-stats';

export const InitialVSData: VulnScanDataTransformed = {
  vulnScanSummary: [],
  vulnScanKeyMetrics: [],
  detectedServicesKeyMetrics: [],
  detectedHostsKeyMetrics: [],
  detectedHostsTop5VulnerableHosts: [],
  topVulnerabilities: [],
  topKevVulnerabilities: [],
  riskyServices: [],
  severityByProminence: []
};

export const NO_DATA_FALLBACK_LABEL =
  'No results found. if unexpected, please submit an entry using the Support menu.';
