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
  const userType = user?.user_type || 'standard';
  const adminUsers = new Set(['globalView', 'globalAdmin', 'regionalAdmin']);
  const noDataMsgPart1 = 'There is no data available for ';
  const noDataMsgPart2 = adminUsers.has(userType) ? 'this' : 'your';
  useClearFiltersOnMount(filters, removeFilter);
  const { orgId, orgName } = useOrgInfo(filters, currentOrganization);
  const {
    data: vulnScanData,
    loading,
    error
  } = useVulnScanData(orgId ? orgId : currentOrganization?.id);
  const assetsOwned = vulnScanData.vulnScanSummary[0]?.assetsOwned;
  const hostsScanned = vulnScanData.vulnScanSummary[0]?.hostsScanned;

  if (loading) {
    return (
      <PageSection>
        <CircularProgress />
      </PageSection>
    );
  }
  if (error || isDataEmpty(vulnScanData)) {
    const noDataUserType =
      error === 'NO_DATA' ? 'standard' : userType || 'standard';
    return (
      <PageSection>
        <NoDataMessage userType={noDataUserType} />
      </PageSection>
    );
  } else if (assetsOwned === 0 || hostsScanned === 0) {
    return (
      <PageSection>
        <NoDataMessage
          userType={userType || 'standard'}
          headerMsg={`${noDataMsgPart1}${noDataMsgPart2} organization.`}
          customMessage={
            adminUsers ? (
              <>Please select another organization from the filter options.</>
            ) : (
              <>
                Please notify the CyHy team using the{' '}
                <Link href={MAILTO_INQUIRY} target="_blank" rel="noopener">
                  General Questions
                </Link>{' '}
                option in the Support menu.
              </>
            )
          }
        />
      </PageSection>
    );
  } else if (
    vulnScanData.vulnScanSummary[0]?.recentlyEnrolled &&
    hostsScanned === 0
  ) {
    return (
      <PageSection>
        <NoDataMessage
          userType={userType || 'standard'}
          headerMsg={
            adminUsers
              ? `${noDataMsgPart1}${noDataMsgPart2} organization.`
              : `${noDataMsgPart1}${noDataMsgPart2} organization at this time, please check back soon to see your data. In the meantime, you can explore helpful resources in the Learning Center.`
          }
          customMessage={
            adminUsers ? (
              <>Please select another organization from the filter options.</>
            ) : (
              <></>
            )
          }
        />
      </PageSection>
    );
  } else if (isEmptyAfterScans(vulnScanData)) {
    return (
      <VulnerabilityScan
        orgId={orgId}
        orgName={orgName}
        vulnScanData={vulnScanData}
        isKeyMetricsNull={true}
        alertMsg={
          <>
            Discovery and assets scans were completed for
            {adminUsers.has(userType) ? ' this ' : ' your '}
            organization, but no data is available. Please{' '}
            {adminUsers.has(userType) ? (
              "modify filter to see other organization's results."
            ) : (
              <>
                contact the CyHy team through Support under{' '}
                <Link
                  href={MAILTO_INQUIRY}
                  target="_blank"
                  rel="noopener"
                  sx={{ fontWeight: '600' }}
                >
                  General Questions
                </Link>
                .
              </>
            )}
          </>
        }
      />
    );
  } else if (isEmptyAfterScans(vulnScanData) && hostsScanned > 0) {
    return (
      <VulnerabilityScan
        orgId={orgId}
        orgName={orgName}
        vulnScanData={vulnScanData}
        isKeyMetricsNull={true}
        alertMsg={<>TO ADD</>}
      />
    );
  }
  return (
    <VulnerabilityScan
      orgId={orgId}
      orgName={orgName}
      vulnScanData={vulnScanData}
      isKeyMetricsNull={false}
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
