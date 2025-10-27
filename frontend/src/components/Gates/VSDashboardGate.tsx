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
  } else if (isEmptyAfterScans(vulnScanData)) {
    return (
      <VulnerabilityScan
        orgId={orgId}
        orgName={orgName}
        vulnScanData={vulnScanData}
        isKeyMetricsNull={true}
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
