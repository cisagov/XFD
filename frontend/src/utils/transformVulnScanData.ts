import {
  StatsTrendsRawData,
  vulnScanDataTransformed
} from 'types/vuln-scan-stats';

export function formatShortDate(
  dateInput: string | Date | null | undefined
): string {
  if (!dateInput) return 'N/A';

  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return 'Invalid Date';

  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

// Utility function to get the latest summary based on summary_date and transform the data.
// This function is not needed when no dates are provided, but should be kept in case there are multiple entries.
function getLatestSummary<T extends { summary_date?: string | null }>(
  summaries: T[]
): T | undefined {
  if (!summaries || summaries.length === 0) return undefined;

  return summaries.reduce((latest, current) => {
    const latestDate = latest.summary_date
      ? new Date(latest.summary_date)
      : new Date(0);
    const currentDate = current.summary_date
      ? new Date(current.summary_date)
      : new Date(0);
    return currentDate > latestDate ? current : latest;
  }, summaries[0]);
}

export const transformVulnScanData = (
  data: StatsTrendsRawData
): vulnScanDataTransformed => {
  const latestVulnSummary = getLatestSummary(data.vuln_scan_summaries);
  const latestHostSummary = getLatestSummary(data.host_summaries);
  const latestPortScanSummary = getLatestSummary(data.port_scan_summaries);
  // const latestPortServiceSummary = getLatestSummary(
  //   data.port_scan_service_summaries
  // );
  if (!latestVulnSummary && !latestHostSummary && !latestPortScanSummary) {
    return {
      vulnScanSummary: [],
      vulnScanKeyMetrics: [],
      detectedServicesKeyMetrics: [],
      detectedHostsKeyMetrics: [],
      detectedHostsTop5VulnerableHosts: [],
      topVulnerabilities: [],
      topKevVulnerabilities: [],
      riskyServices: [],
      severityByProminence: []
    }; // return empty arrays if no data
  }
  return {
    vulnScanSummary: [
      {
        hostScan:
          formatShortDate(latestHostSummary?.start_date) +
          ' - ' +
          formatShortDate(latestHostSummary?.end_date),
        vulnerabilityScan:
          formatShortDate(latestVulnSummary?.start_date) +
          ' - ' +
          formatShortDate(latestVulnSummary?.end_date),
        assetsOwned: latestVulnSummary?.assets_owned_count ?? 0,
        assetsScanned: latestVulnSummary?.scanned_asset_count ?? 0,
        startDate: latestVulnSummary?.start_date ?? '',
        endDate: latestVulnSummary?.end_date ?? ''
      }
    ],
    vulnScanKeyMetrics: [
      {
        title: 'Detected KEVs',
        value:
          (latestVulnSummary?.low_kev_count ?? 0) +
          (latestVulnSummary?.medium_kev_count ?? 0) +
          (latestVulnSummary?.high_kev_count ?? 0) +
          (latestVulnSummary?.critical_kev_count ?? 0),
        hasLink: true,
        startDate: latestVulnSummary?.start_date ?? '',
        endDate: latestVulnSummary?.end_date ?? '',
        dateRange:
          formatShortDate(latestVulnSummary?.start_date) +
          ' - ' +
          formatShortDate(latestVulnSummary?.end_date)
      },
      {
        title: 'Detected Vulnerabilities',
        value:
          (latestVulnSummary?.low_severity_count ?? 0) +
          (latestVulnSummary?.medium_severity_count ?? 0) +
          (latestVulnSummary?.high_severity_count ?? 0) +
          (latestVulnSummary?.critical_severity_count ?? 0),
        hasLink: true,
        startDate: latestVulnSummary?.start_date ?? '',
        endDate: latestVulnSummary?.end_date ?? '',
        dateRange:
          formatShortDate(latestVulnSummary?.start_date) +
          ' - ' +
          formatShortDate(latestVulnSummary?.end_date)
      },
      {
        title: 'Distinct Vulnerabilities',
        value:
          (latestVulnSummary?.unique_low_severity_count ?? 0) +
          (latestVulnSummary?.unique_medium_severity_count ?? 0) +
          (latestVulnSummary?.unique_high_severity_count ?? 0) +
          (latestVulnSummary?.unique_critical_severity_count ?? 0)
      },
      {
        title: 'False Positives',
        value: latestVulnSummary?.false_positive_count ?? 0
      }
    ],
    detectedServicesKeyMetrics: [
      {
        title: 'Detected Services',
        value: latestPortScanSummary?.open_port_count ?? 0
      },
      {
        title: 'Potentially Risky Services',
        value: latestPortScanSummary?.risky_port_count ?? 0
      },
      {
        title: 'Potential NMI Services',
        value: latestPortScanSummary?.nmi_service_count ?? 0
      }
    ],
    detectedHostsKeyMetrics: [
      {
        title: 'Detected Hosts',
        value: latestHostSummary?.up_host_count ?? 0
      },
      {
        title: 'Vulnerable Hosts',
        value: latestVulnSummary?.vulnerable_host_count ?? 0
      },
      {
        title: 'Hosts with Unsupported Software',
        value: latestVulnSummary?.unsupported_software_count ?? 0
      }
    ],
    detectedHostsTop5VulnerableHosts: Object.entries(
      latestVulnSummary?.top_5_risky_hosts ?? {}
    ).map(([hostName, hostData]: [string, any]) => ({
      hostName,
      lowSeverity: hostData.low ?? 0,
      mediumSeverity: hostData.medium ?? 0,
      highSeverity: hostData.high ?? 0,
      criticalSeverity: hostData.critical ?? 0,
      all: hostData.total ?? 0,
      rrs: hostData.rrs ?? 0,
      domainId: hostData.domain_id ?? 0
    })),
    topVulnerabilities: latestVulnSummary?.top_5_occurring_cves ?? [],
    topKevVulnerabilities: latestVulnSummary?.top_5_occurring_kevs ?? [],
    riskyServices: [
      {
        serviceName: 'FTP',
        count: latestPortScanSummary?.risky_service_group_counts?.ftp ?? 0
      },
      {
        serviceName: 'SQL',
        count: latestPortScanSummary?.risky_service_group_counts?.sql ?? 0
      },
      {
        serviceName: 'NETBIOS',
        count: latestPortScanSummary?.risky_service_group_counts?.netbios ?? 0
      },
      {
        serviceName: 'LDAP',
        count: latestPortScanSummary?.risky_service_group_counts?.ldap ?? 0
      },
      {
        serviceName: 'RPC',
        count: latestPortScanSummary?.risky_service_group_counts?.rpc ?? 0
      },
      {
        serviceName: 'IRC',
        count: latestPortScanSummary?.risky_service_group_counts?.irc ?? 0
      },
      {
        serviceName: 'KERBEROS',
        count: latestPortScanSummary?.risky_service_group_counts?.kerberos ?? 0
      },
      {
        serviceName: 'RDP',
        count: latestPortScanSummary?.risky_service_group_counts?.rdp ?? 0
      },
      {
        serviceName: 'TELNET',
        count: latestPortScanSummary?.risky_service_group_counts?.telnet ?? 0
      },
      {
        serviceName: 'SMB',
        count: latestPortScanSummary?.risky_service_group_counts?.smb ?? 0
      }
    ],
    severityByProminence: [
      {
        vulnType: 'KEV',
        lowSeverity: latestVulnSummary?.low_kev_count ?? 0,
        mediumSeverity: latestVulnSummary?.medium_kev_count ?? 0,
        highSeverity: latestVulnSummary?.high_kev_count ?? 0,
        criticalSeverity: latestVulnSummary?.critical_kev_count ?? 0,
        lowMaxAge: latestVulnSummary?.low_kev_max_age ?? 0,
        mediumMaxAge: latestVulnSummary?.medium_kev_max_age ?? 0,
        highMaxAge: latestVulnSummary?.high_kev_max_age ?? 0,
        criticalMaxAge: latestVulnSummary?.critical_kev_max_age ?? 0
      },
      {
        vulnType: 'Distinct',
        lowSeverity: latestVulnSummary?.unique_low_severity_count ?? 0,
        mediumSeverity: latestVulnSummary?.unique_medium_severity_count ?? 0,
        highSeverity: latestVulnSummary?.unique_high_severity_count ?? 0,
        criticalSeverity: latestVulnSummary?.unique_critical_severity_count ?? 0
      },
      {
        vulnType: 'All',
        lowSeverity: latestVulnSummary?.low_severity_count ?? 0,
        mediumSeverity: latestVulnSummary?.medium_severity_count ?? 0,
        highSeverity: latestVulnSummary?.high_severity_count ?? 0,
        criticalSeverity: latestVulnSummary?.critical_severity_count ?? 0,
        lowMaxAge: latestVulnSummary?.low_max_age ?? 0,
        mediumMaxAge: latestVulnSummary?.medium_max_age ?? 0,
        highMaxAge: latestVulnSummary?.high_max_age ?? 0,
        criticalMaxAge: latestVulnSummary?.critical_max_age ?? 0
      }
    ]
  };
};
