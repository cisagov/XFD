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
// Utils
import isDataEmpty from 'utils/transformVulnScanData';

export interface VulnSeverities {
  label: string;
  sevList: string[];
  disable?: boolean;
  amount?: number;
}

export interface WidgetProps extends BoxProps {
  children?: React.ReactNode;
}

const mailtoLink =
  'mailto:vulnerability@mail.cisa.dhs.gov?subject=Request%20Assistance%20-%20CyHy%20Dashboard&body=Have%20a%20question%3F%20We%27re%20here%20to%20help.%0A%0AIf%20you%20have%20general%20questions%20about%20the%20CyHy%20Dashboard%2C%20such%20as%20how%20it%20relates%20to%20your%20reports%2C%20how%20to%20view%20data%2C%20or%20how%20to%20connect%20with%20your%20Cybersecurity%20Advisor%20(CSA)%2C%20and%20you%20can%27t%20find%20the%20answer%20in%20the%20Learning%20Center%2C%20you%20can%20send%20your%20question%20to%20us%20here.%0A%0AWe%27re%20excited%20to%20help%20you%20and%20will%20make%20sure%20your%20question%20gets%20to%20the%20right%20place.%0A';

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
                <Link href={mailtoLink} target="_blank" rel="noopener">
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
  }
  return (
    <VulnerabilityScan
      orgId={orgId}
      orgName={orgName}
      vulnScanData={vulnScanData}
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
