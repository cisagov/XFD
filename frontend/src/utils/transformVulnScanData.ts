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
  if (
    !data.vuln_scan_summaries ||
    !Array.isArray(data.vuln_scan_summaries) ||
    data.vuln_scan_summaries.length === 0
  ) {
    return {
      vulnScanSummary: [],
      vulnScanKeyMetrics: [],
      detectedServicesKeyMetrics: [],
      detectedHostsKeyMetrics: []
    }; // return empty arrays if no data
  }

  // Find the objects with the latest summary_date
  const latestVulnSummary = getLatestSummary(data.vuln_scan_summaries);
  const latestHostSummary = getLatestSummary(data.host_summaries);
  // const latestPortScanSummary = getLatestSummary(data.port_scan_summaries);
  // const latestPortServiceSummary = getLatestSummary(
  //   data.port_scan_service_summaries
  // );

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
        assetsScanned: latestVulnSummary?.scanned_asset_count ?? 0
      }
    ],
    vulnScanKeyMetrics: [
      {
        title: 'Detected Kevs',
        value:
          (latestVulnSummary?.low_kev_count ?? 0) +
          (latestVulnSummary?.medium_kev_count ?? 0) +
          (latestVulnSummary?.high_kev_count ?? 0) +
          (latestVulnSummary?.critical_kev_count ?? 0)
      },
      {
        title: 'Detected Vulnerabilities',
        value:
          (latestVulnSummary?.low_severity_count ?? 0) +
          (latestVulnSummary?.medium_severity_count ?? 0) +
          (latestVulnSummary?.high_severity_count ?? 0) +
          (latestVulnSummary?.critical_severity_count ?? 0)
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
        value: 0 // placeholder value
      },
      {
        title: 'Potentially Risky Services',
        value: 0 // placeholder value
      },
      {
        title: 'Potential NMI Services',
        value: 0 // placeholder value
      }
    ],
    detectedHostsKeyMetrics: [
      {
        title: 'Detected Hosts',
        value: 0 // placeholder value
      },
      {
        title: 'Vulnerable Hosts',
        value: 0 // placeholder value
      },
      {
        title: 'Hosts with Unsupported Software',
        value: 0 // placeholder value
      }
    ]
  };
};
