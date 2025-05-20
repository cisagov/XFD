import React, { useCallback, useState, useEffect, useMemo } from 'react';
import classes from './Risk.module.scss';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Paper,
  Typography,
  CircularProgress,
  Stack,
  Alert
} from '@mui/material';
import VulnerabilityCard from './VulnerabilityCard';
import TopVulnerablePorts from './TopVulnerablePorts';
import TopVulnerableDomains from './TopVulnerableDomains';
import VulnerabilityBarChart from './VulnerabilityBarChart';
import * as RiskStyles from './style';
import { getSeverityColor, offsets, severities } from './utils';
import { ContextType, useAuthContext } from 'context';
import { geoCentroid } from 'd3-geo';
import {
  ComposableMap,
  Geographies,
  Geography,
  ZoomableGroup,
  Marker,
  Annotation
} from 'react-simple-maps';
import { scaleLinear } from 'd3-scale';
import { Stats, Vulnerability } from 'types';
import { UpdateStateForm } from 'components/Register';
import {
  ORGANIZATION_FILTER_KEY,
  OrganizationShallow,
  REGION_FILTER_KEY
} from 'components/RegionAndOrganizationFilters';
import { withSearch } from '@elastic/react-search-ui';
import { FilterTags } from 'pages/Search/FilterTags';
import { useLocation } from 'react-router-dom';
import { useUserTypeFilters } from 'hooks/useUserTypeFilters';
import { useStaticsContext } from 'context/StaticsContext';
import { useUserLevel } from 'hooks/useUserLevel';
import { LoginBlockedDialog } from 'components/LoginBlockedDialog';
import InfoLabel from './InfoLabel';

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

// Color Scale used for map
let colorScale = scaleLinear<string>()
  .domain([0, 1])
  .range(['#c7e8ff', '#135787']);

const Risk: React.FC<ContextType> = ({
  filters,
  removeFilter,
  addFilter,
  search_term,
  setSearchTerm
}) => {
  const {
    showMaps,
    user,
    apiPost,
    apiGet,
    logout,
    userMustSign,
    isLoggingOut
  } = useAuthContext();

  const [stats, setStats] = useState<Stats | undefined>(undefined);
  const [isUpdateStateFormOpen, setIsUpdateStateFormOpen] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const RiskRoot = RiskStyles.RiskRoot;
  const { cardRoot, content, contentWrapper, header, panel } =
    RiskStyles.classesRisk;

  const geoStateUrl = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json';

  // const allColors = ['rgb(0, 111, 162)', 'rgb(0, 185, 227)'];

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

  const { pathname } = useLocation();

  const filtersToDisplay = useMemo(() => {
    if (search_term !== '') {
      return [
        ...filters,
        {
          field: 'query',
          values: [search_term],
          onClear: () => setSearchTerm('', { shouldClearFilters: false })
        }
      ];
    }
    return filters;
  }, [filters, search_term, setSearchTerm]);

  const userLevel = useUserLevel().userLevel;

  const { regions } = useStaticsContext();
  const initialFiltersForUser = useUserTypeFilters(regions, user, userLevel);

  const fetchStats = useCallback(
    async (org_id?: string) => {
      if (
        user?.user_type === 'globalAdmin' &&
        riskFilters.regions.length === 0
      ) {
        return;
      } else {
        const { result } = await apiPost<ApiResponse>('/stats', {
          body: {
            filters: riskFilters
          }
        });
        const max = Math.max(
          ...result.vulnerabilities.by_org.map((p) => p.value)
        );
        colorScale = scaleLinear<string>()
          .domain([0, Math.log(max)])
          .range(['#c7e8ff', '#135787']);
        setStats(result);
      }
    },

    // eslint-disable-next-line react-hooks/exhaustive-deps
    [riskFilters]
  );

  const [isLoginBlockedDialogOpen, setIsLoginBlockedDialogOpen] =
    useState(false);
  const [maintenanceNotification, setMaintenanceNotification] =
    useState<any>(null);

  useEffect(() => {
    fetchStats();
  }, [fetchStats, riskFilters]);

  useEffect(() => {
    if (!isLoggingOut && user) {
      if (!user.state || user.state === '') {
        setIsUpdateStateFormOpen(true);
      }
    }
  }, [user, isLoggingOut]);

  useEffect(() => {
    const fetchAndCheckMaintenance = async () => {
      // TODO: Some login blocking logic is a duplicate of backend
      // checks to meet "waiting room" needs to allow controlled logins
      // for populating new user state and terms agreement before blocking
      // for pre-release. Standardize this once this is no longer needed.
      if (
        user &&
        !user.invite_pending &&
        user.state &&
        user.date_accepted_terms &&
        !isLoginBlockedDialogOpen
      ) {
        // Active Notifications
        const notifications = await apiGet('/notifications');
        const active = notifications.find(
          (n: any) =>
            n.status === 'active' &&
            n.maintenance_type === 'major' &&
            new Date(n.start_datetime) <= new Date() &&
            new Date(n.end_datetime) >= new Date()
        );
        // Set non-blocking userTypes (additional check)
        const nonBlockingUserTypes = ['globalAdmin', 'regionalAdmin'];
        if (active && !nonBlockingUserTypes.includes(user.user_type)) {
          setMaintenanceNotification(active);
          setIsLoginBlockedDialogOpen(true);
        }
      }
    };

    fetchAndCheckMaintenance();
  }, [apiGet, isLoginBlockedDialogOpen, user, userMustSign]);

  useEffect(() => {
    const handleMaintenanceBlocked = (e: any) => {
      if (e.detail?.message) {
        setMaintenanceNotification({ message: e.detail.message });
        setIsLoginBlockedDialogOpen(true);
      }
    };

    window.addEventListener('maintenance-blocked', handleMaintenanceBlocked);

    return () => {
      window.removeEventListener(
        'maintenance-blocked',
        handleMaintenanceBlocked
      );
    };
  }, []);

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
  }, [
    pathname,
    removeFilter,
    filters,
    addFilter,
    riskFilters,
    initialFiltersForUser
  ]);

  const MapCard = ({
    title,
    geoUrl,
    findFn
  }: {
    title: string;
    geoUrl: string;
    findFn: (geo: any) => Point | undefined;
    type: string;
  }) => (
    <Paper elevation={0}>
      <div className={classes.chart}>
        <div className={header}>
          <h2>{title}</h2>
        </div>
        <ComposableMap
          data-tip="hello world"
          projection="geoAlbersUsa"
          style={{
            width: '90%',
            display: 'block',
            margin: 'auto'
          }}
        >
          <ZoomableGroup zoom={1}>
            <Geographies geography={geoUrl}>
              {({ geographies }) =>
                geographies.map((geo) => {
                  const cur = findFn(geo) as
                    | (Point & {
                        org_id: string;
                      })
                    | undefined;
                  const centroid = geoCentroid(geo);
                  const name: string = geo.properties.name;
                  return (
                    <React.Fragment key={geo.rsmKey}>
                      <Geography
                        geography={geo}
                        fill={colorScale(cur ? Math.log(cur.value) : 0)}
                        onClick={() => {
                          if (cur) fetchStats(cur.org_id);
                        }}
                      />
                      <g>
                        {centroid[0] > -160 &&
                          centroid[0] < -67 &&
                          (Object.keys(offsets).indexOf(name) === -1 ? (
                            <Marker coordinates={centroid}>
                              <text y="2" fontSize={14} textAnchor="middle">
                                {cur ? cur.value : 0}
                              </text>
                            </Marker>
                          ) : (
                            <Annotation
                              subject={centroid}
                              dx={offsets[name][0]}
                              dy={offsets[name][1]}
                              connectorProps={{}}
                            >
                              <text
                                x={4}
                                fontSize={14}
                                alignmentBaseline="middle"
                              >
                                {cur ? cur.value : 0}
                              </text>
                            </Annotation>
                          ))}
                      </g>
                    </React.Fragment>
                  );
                })
              }
            </Geographies>
          </ZoomableGroup>
        </ComposableMap>
      </div>
    </Paper>
  );

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

  if (isUpdateStateFormOpen) {
    return (
      <UpdateStateForm
        open={isUpdateStateFormOpen}
        user_id={user?.id ?? ''}
        onClose={async () => {
          setIsUpdateStateFormOpen(false);

          // Re-fetch user data or just check if state now exists
          if (user && user.state) {
            const notifications = await apiGet('/notifications');
            const active = notifications.find(
              (n: any) =>
                n.status === 'active' &&
                n.maintenance_type === 'major' &&
                new Date(n.start_datetime) <= new Date() &&
                new Date(n.end_datetime) >= new Date()
            );
            if (active && user.user_type !== 'globalAdmin') {
              setMaintenanceNotification(active);
              setIsLoginBlockedDialogOpen(true);
            }
          }
        }}
      />
    );
  }

  if (isLoginBlockedDialogOpen && maintenanceNotification) {
    return (
      <LoginBlockedDialog
        open={isLoginBlockedDialogOpen}
        message={maintenanceNotification.message}
        onClose={() => {
          setIsLoginBlockedDialogOpen(false);
          logout();
        }}
      />
    );
  }

  if (user?.invite_pending) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh'
        }}
      >
        <Card style={{ maxWidth: 400, textAlign: 'center' }}>
          <CardContent>
            <Typography variant="h5" component="h2">
              REQUEST SENT
            </Typography>
            <Typography variant="body1">
              Thank you for requesting a CyHy Dashboard account, you will
              receive notification once this request is approved.
            </Typography>
          </CardContent>
        </Card>
      </div>
    );
  }

  const overviewHeader = (
    <Box>
      <Grid container mb={0}>
        <Grid size={{ xs: 12 }} sx={{ mt: 6 }}>
          <InfoLabel
            label="Overview Dashboard"
            typographyVariant="h1"
            //viewDetails
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
        {header}
        <Alert severity="error">{error}</Alert>
      </Stack>
    );
  }

  return (
    <Stack
      sx={{ maxWidth: '1152px', margin: 'auto', paddingBottom: 6 }}
      spacing={6}
    >
      {overviewHeader}
      <Box>
        <Grid
          container
          direction="column"
          border="1px solid"
          borderRadius="4px"
          borderColor="neutrals.main"
          p={3}
          sx={{ backgroundColor: 'neutrals.white' }}
        >
          <Grid
            container
            direction="row"
            paddingBottom={2}
            alignItems="center"
            justifyContent="space-between"
          >
            <Grid size={{ xs: 12 }}>
              <InfoLabel
                label="Summary of CyHy Services Data"
                //viewDetails
                //link="/inventory/vulnerabilities"
              />
            </Grid>
          </Grid>
          <Grid container direction="row" spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Box
                border="1px solid"
                borderRadius="4px"
                borderColor="neutrals.light"
                p={3}
              >
                <VulnerabilityCard
                  label={
                    <InfoLabel
                      label="Latest Vulnerabilities"
                      typographyVariant="h3"
                      headingLevel="h3"
                      viewDetails
                      link="/inventory/vulnerabilities"
                    />
                  }
                  data={latestVulnsGroupedArr}
                  showLatest={true}
                  showCommon={false}
                />
              </Box>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Box
                border="1px solid"
                borderRadius="4px"
                borderColor="neutrals.light"
                p={3}
              >
                <VulnerabilityCard
                  label={
                    <InfoLabel
                      label="Most Common Vulnerabilities"
                      typographyVariant="h3"
                      headingLevel="h3"
                      viewDetails
                      link="/inventory/vulnerabilities"
                    />
                  }
                  data={
                    stats?.vulnerabilities?.most_common_vulnerabilities || []
                  }
                  showLatest={false}
                  showCommon={true}
                />
              </Box>
            </Grid>
          </Grid>
        </Grid>
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
    search_term,
    setSearchTerm
  }: ContextType) => ({
    addFilter,
    removeFilter,
    filters,
    facets,
    search_term,
    setSearchTerm
  })
)(Risk);

export default Risk;
