import React, { useCallback, useState, useEffect, useMemo } from 'react';
import { Box, Grid, CircularProgress, Stack, Alert } from '@mui/material';
import TopVulnerablePorts from './TopVulnerablePorts';
import VulnerabilityBarChart from './VulnerabilityBarChart';
import { getSeverityColor, severities } from './utils';
import { ContextType, useAuthContext } from 'context';

// import TopVulnerableDomains from './TopVulnerableDomains';
import { Stats, Vulnerability } from 'types';
import {
  ORGANIZATION_FILTER_KEY,
  OrganizationShallow,
  REGION_FILTER_KEY
} from 'components/FilterDrawer/RegionAndOrganizationFilters';
import { withSearch } from '@elastic/react-search-ui';
import { useUserTypeFilters } from 'hooks/useUserTypeFilters';
import { useStaticsContext } from 'context/StaticsContext';
import { useUserLevel } from 'hooks/useUserLevel';
import InfoLabel from 'components/Dashboard/InfoLabel';
import MostCommonVulns from './MostCommonVulns';
import LatestKEVs from './LatestKEVs';
import infoIconContent from './infoIconContent.json';
import OpenVulnsByHosts from './OpenVulnsByHosts';

export interface Point {
  id: string;
  label: string;
  value: number;
}

interface ApiResponse {
  result: Stats;
}

interface VulnerabilityCount extends Vulnerability {
  count: number;
}

export interface VulnSeverities {
  label: string;
  sevList: string[];
  disable?: boolean;
  amount?: number;
}

const tooltipContentJson = infoIconContent.infoIconContent;

const OverviewDash: React.FC<ContextType> = ({
  filters,
  removeFilter,
  addFilter
  // searchTerm,
  // setSearchTerm
}) => {
  const { user, apiPost } = useAuthContext();

  const [stats, setStats] = useState<Stats | undefined>(undefined);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const riskFilters = useMemo(() => {
    const regionFilters = filters.find(
      (filter) => filter.field === REGION_FILTER_KEY
    );
    const organizationFilters = filters.find(
      (filter) => filter.field === ORGANIZATION_FILTER_KEY
    );
    return {
      regions:
        regionFilters && regionFilters.values.length > 0
          ? regionFilters.values
          : [],
      organizations:
        organizationFilters && organizationFilters.values.length > 0
          ? organizationFilters.values.map(
              (item: OrganizationShallow) => item.id
            )
          : []
    };
  }, [filters]);

  // const filtersToDisplay = useMemo(() => {
  //   if (searchTerm !== '') {
  //     return [
  //       ...filters,
  //       {
  //         field: 'query',
  //         values: [searchTerm],
  //         onClear: () => setSearchTerm('', { shouldClearFilters: false })
  //       }
  //     ];
  //   }
  //   return filters;
  // }, [filters, searchTerm, setSearchTerm]);

  const userLevel = useUserLevel().userLevel;

  const { regions } = useStaticsContext();
  const initialFiltersForUser = useUserTypeFilters(regions, user, userLevel);

  const fetchStats = useCallback(
    async (org_id?: string) => {
      setLoading(true);
      setError(null);
      if (
        user?.user_type === 'globalAdmin' &&
        riskFilters.regions.length === 0
      ) {
        return;
      } else {
        try {
          const { result } = await apiPost<ApiResponse>('/stats', {
            body: {
              filters: riskFilters
            }
          });
          // const max = Math.max(
          //   ...result.vulnerabilities.by_org.map((p) => p.value)
          // );
          setStats(result);
          setLoading(false);
        } catch (err) {
          setLoading(false);
          setError(
            err + '. Unable to retrieve data. See console log for details.'
          );
        }
      }
    },

    // eslint-disable-next-line react-hooks/exhaustive-deps
    [riskFilters]
  );

  useEffect(() => {
    fetchStats();
  }, [fetchStats, riskFilters]);

  useEffect(() => {
    filters.forEach((filter) => {
      if (
        filter.field !== 'organization.region_id' &&
        filter.field !== 'organization_id'
      ) {
        removeFilter(filter.field, filter.values[0], filter.type);
      }
    });
    if (filters.length === 0) {
      initialFiltersForUser.forEach((filter) => {
        filter.values.forEach((val) => {
          addFilter(filter.field, val, filter.type);
        });
      });
    }
  }, [removeFilter, filters, addFilter, initialFiltersForUser]);

  const latestVulnsGrouped: {
    [key: string]: VulnerabilityCount;
  } = {};
  if (stats) {
    for (const vuln of stats.vulnerabilities.latest_vulnerabilities) {
      if (vuln.title in latestVulnsGrouped)
        latestVulnsGrouped[vuln.title].count++;
      else {
        latestVulnsGrouped[vuln.title] = { ...vuln, count: 1 };
      }
    }
  }

  const latestVulnsGroupedArr = Object.values(latestVulnsGrouped).sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  if (stats) {
    for (const sev of severities) {
      sev.disable = !stats.domains.num_vulnerabilities.some((i) =>
        sev.sevList.includes(i.id.split('|')[1])
      );
    }
  }

  const overviewHeader = (
    <Box>
      <Grid container mb={0}>
        <Grid size={{ xs: 12 }} sx={{ mt: 6 }}>
          <InfoLabel
            label="Overview Dashboard"
            typographyVariant="h1"
            tooltipContentJson={tooltipContentJson}
          />
        </Grid>
      </Grid>
    </Box>
  );

  if (loading) {
    return <CircularProgress />;
  }
  if (error) {
    return (
      <Stack
        sx={{ maxWidth: '1152px', margin: 'auto', paddingBottom: 6 }}
        spacing={6}
      >
        {overviewHeader}
        <Alert severity="error">{error}</Alert>
      </Stack>
    );
  }

  return (
    <Stack
      sx={{ maxWidth: '1152px', margin: 'auto', paddingBottom: 3 }}
      spacing={6}
    >
      {overviewHeader}
      <Box>
        {stats && (
          <Grid
            // Most outer container
            container
            border="1px solid"
            borderRadius="4px"
            borderColor="neutrals.main"
            spacing={2}
            padding={3}
            sx={{ backgroundColor: 'neutrals.white' }}
          >
            {/* Top Header grid row */}
            <Grid
              alignItems="center"
              justifyContent="space-between"
              size={{ xs: 12 }}
            >
              <InfoLabel
                label="Summary of CyHy Services Data"
                tooltipContentJson={tooltipContentJson}
              />
            </Grid>
            {/* Main content */}
            <Grid size={{ xs: 12 }}>
              <Grid container spacing={2} width="100%">
                {/* Left side content */}
                <Grid size={{ xs: 12, sm: 12, md: 6 }}>
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 12 }}>
                      <LatestKEVs data={latestVulnsGroupedArr} />
                    </Grid>
                    <Grid size={{ xs: 12 }}>
                      <OpenVulnsByHosts
                        data={stats.domains.num_vulnerabilities}
                      />
                    </Grid>
                  </Grid>
                </Grid>
                {/* Right side content */}
                <Grid size={{ xs: 12, sm: 12, md: 6 }}>
                  <Grid container spacing={2} width="100%">
                    <Grid size={{ xs: 12 }}>
                      <Box
                        border="1px solid"
                        borderRadius="4px"
                        borderColor="neutrals.light"
                        px={3}
                        py={2}
                      >
                        <InfoLabel
                          label="Vulnerability by Severity Type"
                          typographyVariant="h3"
                          headingLevel="h3"
                          viewDetails
                          link="/inventory/vulnerabilities"
                          tooltipContentJson={tooltipContentJson}
                        />
                        {stats.vulnerabilities.severity.length > 0 && (
                          <VulnerabilityBarChart
                            title="Severity Levels"
                            data={stats.vulnerabilities.severity}
                            colors={getSeverityColor}
                            type="vulns"
                          />
                        )}
                      </Box>
                    </Grid>
                    {/* <Grid size={{ xs: 12 }}>
                      <Box
                        border="1px solid"
                        borderRadius="4px"
                        borderColor="neutrals.light"
                        px={3}
                        py={2}
                      >
                        <InfoLabel
                          label="Vulnerabilities by Organizations"
                          typographyVariant="h3"
                          headingLevel="h3"
                          viewDetails
                          link="/inventory/vulnerabilities"
                          tooltipContentJson={tooltipContentJson}
                        />
                        {stats.vulnerabilities.by_org.length > 0 && (
                          <VulnerabilityBarChart
                            title="Vulnerabilities by Organizations"
                            data={stats.vulnerabilities.by_org}
                            colors={getSeverityColor}
                            type="vulns"
                          />
                        )}
                      </Box>
                    </Grid> */}
                    <Grid size={{ xs: 12 }}>
                      <MostCommonVulns
                        data={stats.vulnerabilities.most_common_vulnerabilities}
                      />
                    </Grid>
                    <Grid size={{ xs: 12 }}>
                      <Box
                        border="1px solid"
                        borderRadius="4px"
                        borderColor="neutrals.light"
                        px={3}
                        py={2}
                      >
                        <InfoLabel
                          label="Most Common Ports"
                          typographyVariant="h3"
                          headingLevel="h3"
                          viewDetails
                          link="/inventory/vulnerabilities"
                          tooltipContentJson={tooltipContentJson}
                        />
                        {stats.domains.ports.length > 0 && (
                          <TopVulnerablePorts
                            data={stats.domains.ports.slice(0, 5).reverse()}
                          />
                        )}
                      </Box>
                    </Grid>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        )}
      </Box>
    </Stack>
  );
};

//Use this as a reference point for the VS Dash UI
export const RiskWithSearch = withSearch(
  ({
    addFilter,
    removeFilter,
    filters,
    facets,
    searchTerm,
    setSearchTerm
  }: ContextType) => ({
    addFilter,
    removeFilter,
    filters,
    facets,
    searchTerm,
    setSearchTerm
  })
)(OverviewDash);

export default OverviewDash;
