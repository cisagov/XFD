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

export const EmptyVSData: VulnScanDataTransformed = {
  vulnScanSummary: [
    {
      hostScan: 'October 27, 2025',
      vulnerabilityScan: 'October 24, 2025',
      assetsOwned: 0,
      hostsScanned: 0,
      startDate: '',
      endDate: '2025-10-24T22:24:52.664Z',
      enrolledDate: '',
      recentlyEnrolled: false
    }
  ],
  vulnScanKeyMetrics: [
    {
      title: 'Detected KEVs',
      value: 0,
      hasLink: true,
      startDate: '',
      endDate: '',
      dateRange: 'No Dates Available'
    },
    {
      title: 'Detected Vulnerabilities',
      value: 0,
      hasLink: true,
      startDate: '',
      endDate: '',
      dateRange: 'No Dates Available'
    },
    {
      title: 'Distinct Vulnerabilities',
      value: 0
    },
    {
      title: 'False Positives',
      value: 0
    }
  ],
  detectedServicesKeyMetrics: [
    {
      title: 'Detected Services',
      value: 0
    },
    {
      title: 'Potentially Risky Services',
      value: 0
    },
    {
      title: 'Potential NMI Services',
      value: 0
    }
  ],
  detectedHostsKeyMetrics: [
    {
      title: 'Detected Hosts',
      value: 0
    },
    {
      title: 'Vulnerable Hosts',
      value: 0
    },
    {
      title: 'Hosts with Unsupported Software',
      value: 0
    }
  ],
  detectedHostsTop5VulnerableHosts: [],
  topVulnerabilities: [],
  topKevVulnerabilities: [],
  riskyServices: [
    {
      serviceName: 'FTP',
      count: 0
    },
    {
      serviceName: 'SQL',
      count: 0
    },
    {
      serviceName: 'NETBIOS',
      count: 0
    },
    {
      serviceName: 'LDAP',
      count: 0
    },
    {
      serviceName: 'RPC',
      count: 0
    },
    {
      serviceName: 'IRC',
      count: 0
    },
    {
      serviceName: 'KERBEROS',
      count: 0
    },
    {
      serviceName: 'RDP',
      count: 0
    },
    {
      serviceName: 'TELNET',
      count: 0
    },
    {
      serviceName: 'SMB',
      count: 0
    }
  ],
  severityByProminence: [
    {
      vulnType: 'KEV',
      lowSeverity: 0,
      mediumSeverity: 0,
      highSeverity: 0,
      criticalSeverity: 0,
      lowMaxAge: 0,
      mediumMaxAge: 0,
      highMaxAge: 0,
      criticalMaxAge: 0
    },
    {
      vulnType: 'Distinct',
      lowSeverity: 0,
      mediumSeverity: 0,
      highSeverity: 0,
      criticalSeverity: 0
    },
    {
      vulnType: 'All',
      lowSeverity: 0,
      mediumSeverity: 0,
      highSeverity: 0,
      criticalSeverity: 0,
      lowMaxAge: 0,
      mediumMaxAge: 0,
      highMaxAge: 0,
      criticalMaxAge: 0
    }
  ]
};
