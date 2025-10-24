import React from 'react';
import { withSearch } from '@elastic/react-search-ui';
import { BoxProps, CircularProgress, Link } from '@mui/material';
// Context & hooks
import { ContextType, useAuthContext } from 'context';
import { useVulnScanData } from 'hooks/useVulnScanData';
import { useClearFiltersOnMount } from 'hooks/useClearFiltersOnMount';
import { useOrgInfo } from 'hooks/useOrgInfo';
// Shared components
import NoDataMessage from 'components/Dashboard/NoDataMessage';
import PageSection from 'components/Dashboard/PageSection';
import { VulnerabilityScan } from 'pages/VulnerabilityScanDash/VulnerabilityScan';
// Internal imports
import isDataEmpty from 'utils/transformVulnScanData';
import { isEmptyAfterScans } from 'utils/transformVulnScanData';
import { MAILTO_INQUIRY } from '@/constants/emailLinks';

const testVulnScanData = {
  vulnScanSummary: [
    {
      hostScan: 'October 20, 2025',
      vulnerabilityScan: 'October 16, 2025',
      assetsOwned: 110,
      hostsScanned: 2873,
      startDate: '',
      endDate: '2025-10-17T00:18:58.745Z',
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
      value: 2873
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

export interface VulnSeverities {
  label: string;
  sevList: string[];
  disable?: boolean;
  amount?: number;
}

export interface WidgetProps extends BoxProps {
  children?: React.ReactNode;
}

export const VSDashboardGate: React.FC<{
  filters: any;
  removeFilter: any;
}> = ({ filters, removeFilter }) => {
  const { currentOrganization, user } = useAuthContext();

  useClearFiltersOnMount(filters, removeFilter);

  const { orgId, orgName } = useOrgInfo(filters, currentOrganization);

  const {
    data: vulnScanData,
    loading,
    error
  } = useVulnScanData(orgId ? orgId : currentOrganization?.id);

  if (loading) {
    return (
      <PageSection>
        <CircularProgress />
      </PageSection>
    );
  }
  if (error || isDataEmpty(vulnScanData)) {
    const noDataUserType =
      error === 'NO_DATA' ? 'standard' : user?.user_type || 'standard';
    return (
      <PageSection>
        <NoDataMessage userType={noDataUserType} />
      </PageSection>
    );
  } else if (
    vulnScanData.vulnScanSummary[0]?.assetsOwned === 0 ||
    vulnScanData.vulnScanSummary[0]?.hostsScanned === 0
  ) {
    return (
      <PageSection>
        <NoDataMessage
          userType={user?.user_type || 'standard'}
          headerMsg={`There is no data available for ${
            (user?.user_type || 'standard') === 'standard' ? 'your' : 'this'
          } organization.`}
          customMessage={
            (user?.user_type || 'standard') === 'standard' ? (
              <>
                Please notify the CyHy team using the{' '}
                <Link href={MAILTO_INQUIRY} target="_blank" rel="noopener">
                  General Questions
                </Link>{' '}
                option in the Support menu.
              </>
            ) : (
              <>Please select another organization from the filter options.</>
            )
          }
        />
      </PageSection>
    );
  } else if (
    vulnScanData.vulnScanSummary[0]?.recentlyEnrolled &&
    vulnScanData.vulnScanSummary[0]?.hostsScanned === 0
  ) {
    return (
      <PageSection>
        <NoDataMessage
          userType={user?.user_type || 'standard'}
          headerMsg={
            (user?.user_type || 'standard') === 'standard'
              ? 'There is no data available for your organization at this time, please check back soon to see your data. In the meantime, you can explore helpful resources in the Learning Center.'
              : 'There is no data available for this organization.'
          }
          customMessage={
            (user?.user_type || 'standard') === 'standard' ? (
              <></>
            ) : (
              <>Please select another organization from the filter options.</>
            )
          }
        />
      </PageSection>
    );
  } else if (isEmptyAfterScans(testVulnScanData)) {
    return (
      <VulnerabilityScan
        orgId={orgId}
        orgName={orgName}
        vulnScanData={testVulnScanData}
        isKeyMetricsNull={true}
      />
    );
  }
  return (
    <VulnerabilityScan
      orgId={orgId}
      orgName={orgName}
      vulnScanData={testVulnScanData}
    />
  );
};

export const VulnerabilityScanWithSearch = withSearch(
  ({ filters, addFilter, removeFilter }: ContextType) => ({
    filters,
    addFilter,
    removeFilter
  })
)(VSDashboardGate);
