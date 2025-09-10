// utils/transformVulnScanData.ts
import {
  SeverityByProminenceGraphData,
  StatsTrendsRawData,
  VulnScanDataTransformed
} from 'types/vuln-scan-stats';

export const NO_DATA_FALLBACK_LABEL =
  'No results found. if unexpected, please submit an entry using the Support menu.';

export function formatShortDate(
  dateInput: string | Date | null | undefined
): string {
  if (!dateInput) return '';
  const dateObj = new Date(dateInput);
  if (Number.isNaN(dateObj.getTime())) return '';
  return dateObj.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

export function formatRange(
  start?: string | Date | null | undefined,
  end?: string | Date | null | undefined
): string {
  const startStr = formatShortDate(start);
  const endStr = formatShortDate(end);
  if (!startStr && !endStr) return 'No Dates Available';
  // Ensures only end date is shown per CRASM-3140
  if (startStr && endStr) return `${endStr}`;
  return startStr || endStr;
}

function enrolledWithinTwoWeeks(timestamp?: string | null): boolean {
  if (!timestamp) return false;

  const enrolledDate = new Date(timestamp);
  if (isNaN(enrolledDate.getTime())) return false;

  const now = new Date();
  const twoWeeksInMs = 14 * 24 * 60 * 60 * 1000;

  return now.getTime() - enrolledDate.getTime() <= twoWeeksInMs;
}

// ---------- helpers for fallback ----------
const isBlankLike = (value: unknown) => {
  if (value === null || value === undefined) return true;
  const stringVal = String(value).trim();
  return (
    !stringVal ||
    /^n\/?a$/i.test(stringVal) ||
    /^null$/i.test(stringVal) ||
    /^undefined$/i.test(stringVal)
  );
};

const parseDate = (value: unknown): Date | null => {
  if (isBlankLike(value)) return null;
  const dateObj = new Date(String(value));
  return Number.isNaN(dateObj.getTime()) ? null : dateObj;
};

const formatDateLabel = (dateObj: Date) =>
  new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric'
  }).format(dateObj);

const buildRangeLabel = (
  startValue?: unknown,
  endValue?: unknown
): { label: string | null; start?: string; end?: string } => {
  const startDate = parseDate(startValue);
  const endDate = parseDate(endValue);

  if (startDate && endDate) {
    // Ensures only end date is shown per CRASM-3140
    return { label: formatDateLabel(endDate), end: endDate.toISOString() };
  }
  if (endDate) {
    return { label: formatDateLabel(endDate), end: endDate.toISOString() };
  }
  if (startDate) {
    return {
      label: formatDateLabel(startDate),
      start: startDate.toISOString()
    };
  }

  // If non-empty raw strings didn’t parse, still surface them
  const startRaw = isBlankLike(startValue) ? '' : String(startValue);
  const endRaw = isBlankLike(endValue) ? '' : String(endValue);
  if (startRaw || endRaw) {
    return {
      label:
        startRaw && endRaw ? `${startRaw} - ${endRaw}` : startRaw || endRaw,
      start: startRaw || undefined,
      end: endRaw || undefined
    };
  }
  return { label: null };
};

// Picks the best label and the dates actually used, following the fallback order.
function computeVulnerabilityScanLabel(data: StatsTrendsRawData): {
  label: string;
  usedStart?: string;
  usedEnd?: string;
} {
  const latestVuln = getLatestSummary(data.vuln_scan_summaries);
  const latestHost = getLatestSummary(data.host_summaries);

  // 1) vuln_scan_summaries start/end
  if (
    latestVuln &&
    (!isBlankLike(latestVuln.start_date) || !isBlankLike(latestVuln.end_date))
  ) {
    const range = buildRangeLabel(latestVuln.start_date, latestVuln.end_date);
    if (range.label)
      return { label: range.label, usedStart: range.start, usedEnd: range.end };
  }

  // 2) host_summaries vuln min/max
  if (
    latestHost &&
    (!isBlankLike((latestHost as any).vuln_scan_min_timestamp) ||
      !isBlankLike((latestHost as any).vuln_scan_max_timestamp))
  ) {
    const range = buildRangeLabel(
      (latestHost as any).vuln_scan_min_timestamp,
      (latestHost as any).vuln_scan_max_timestamp
    );
    if (range.label)
      return { label: range.label, usedStart: range.start, usedEnd: range.end };
  }

  // 3) host_summaries net min/max → explicit message, no dates
  if (
    latestHost &&
    (!isBlankLike((latestHost as any).net_scan1_min_timestamp) ||
      !isBlankLike((latestHost as any).net_scan1_max_timestamp))
  ) {
    return { label: 'No active hosts' };
  }

  // 4) fallback message (sentinel)
  return { label: NO_DATA_FALLBACK_LABEL };
}

// unchanged util
function getLatestSummary<T extends { summary_date?: string | null }>(
  summaries: T[] | undefined
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
): VulnScanDataTransformed => {
  const latestVulnSummary = getLatestSummary(data.vuln_scan_summaries);
  const latestHostSummary = getLatestSummary(data.host_summaries);
  const latestPortScanSummary = getLatestSummary(data.port_scan_summaries);

  if (!latestVulnSummary && !latestHostSummary && !latestPortScanSummary) {
    return {
      vulnScanSummary: [
        {
          hostScan: 'Not available',
          vulnerabilityScan: 'Reach out to Vulnerability Mailbox',
          assetsOwned: 0,
          hostsScanned: 0,
          startDate: '',
          endDate: '',
          enrolledDate: '',
          recentlyEnrolled: false
        }
      ],
      vulnScanKeyMetrics: [
        {
          title: 'Detected KEVs',
          value: 0,
          startDate: '',
          endDate: '',
          dateRange: 'Not available'
        },
        {
          title: 'Detected Vulnerabilities',
          value: 0,
          startDate: '',
          endDate: '',
          dateRange: 'Not available'
        },
        { title: 'Distinct Vulnerabilities', value: 0 },
        { title: 'False Positives', value: 0 }
      ],
      detectedServicesKeyMetrics: [
        { title: 'Detected Services', value: 0 },
        { title: 'Potentially Risky Services', value: 0 },
        { title: 'Potential NMI Services', value: 0 }
      ],
      detectedHostsKeyMetrics: [
        { title: 'Detected Hosts', value: 0 },
        { title: 'Vulnerable Hosts', value: 0 },
        { title: 'Hosts with Unsupported Software', value: 0 }
      ],
      detectedHostsTop5VulnerableHosts: [],
      topVulnerabilities: [],
      topKevVulnerabilities: [],
      riskyServices: [],
      severityByProminence: []
    };
  }

  // Build vulnerabilityScan label with fallback (and capture used dates)
  const vulLabel = computeVulnerabilityScanLabel(data);

  return {
    vulnScanSummary: [
      {
        hostScan: formatRange(
          latestHostSummary?.start_date,
          latestHostSummary?.end_date
        ),
        vulnerabilityScan: vulLabel.label,
        assetsOwned: latestVulnSummary?.assets_owned_count ?? 0,
        hostsScanned: latestHostSummary?.up_host_count ?? 0,
        startDate: vulLabel.usedStart ?? '',
        endDate: vulLabel.usedEnd ?? '',
        enrolledDate: latestVulnSummary?.enrolled_in_vs_timestamp ?? '',
        recentlyEnrolled:
          enrolledWithinTwoWeeks(latestVulnSummary?.enrolled_in_vs_timestamp) ??
          false
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
        dateRange: formatRange(
          latestVulnSummary?.start_date,
          latestVulnSummary?.end_date
        )
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
        dateRange: formatRange(
          latestVulnSummary?.start_date,
          latestVulnSummary?.end_date
        )
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
      { title: 'Detected Hosts', value: latestHostSummary?.up_host_count ?? 0 },
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

export function shouldSkipVulnType(
  data: SeverityByProminenceGraphData[],
  typeToCheck: string
): boolean {
  const entry = data.find((item) => item.vulnType === typeToCheck);
  if (!entry) return true;

  const { lowSeverity, mediumSeverity, highSeverity, criticalSeverity } = entry;
  return (
    lowSeverity === 0 &&
    mediumSeverity === 0 &&
    highSeverity === 0 &&
    criticalSeverity === 0
  );
}

export default function isDataEmpty(data: VulnScanDataTransformed) {
  return (
    !data.vulnScanSummary.length &&
    !data.vulnScanKeyMetrics.length &&
    !data.detectedServicesKeyMetrics.length &&
    !data.detectedHostsKeyMetrics.length &&
    !data.detectedHostsTop5VulnerableHosts.length &&
    !data.topVulnerabilities.length &&
    !data.topKevVulnerabilities.length &&
    !data.riskyServices.length &&
    !data.severityByProminence.length
  );
}
