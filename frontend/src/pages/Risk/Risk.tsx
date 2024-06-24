import React, { useCallback, useState, useEffect } from 'react';
import classes from './Risk.module.scss';
import { Card, CardContent, Typography, Paper } from '@mui/material';
import VulnerabilityCard from './VulnerabilityCard';
import TopVulnerablePorts from './TopVulnerablePorts';
import TopVulnerableDomains from './TopVulnerableDomains';
import VulnerabilityPieChart from './VulnerabilityPieChart';
import * as RiskStyles from './style';
import { getSeverityColor, offsets, severities } from './utils';
import { useAuthContext } from 'context';
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
import { Vulnerability } from 'types';
import { UpdateStateForm } from 'components/Register';

export interface Point {
  id: string;
  label: string;
  value: number;
}

interface Stats {
  domains: {
    services: Point[];
    ports: Point[];
    numVulnerabilities: Point[];
    total: number;
  };
  vulnerabilities: {
    severity: Point[];
    byOrg: Point[];
    latestVulnerabilities: Vulnerability[];
    mostCommonVulnerabilities: VulnerabilityCount[];
  };
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

const Risk: React.FC = (props) => {
  const { currentOrganization, showAllOrganizations, showMaps, user, apiPost } =
    useAuthContext();

  const [stats, setStats] = useState<Stats | undefined>(undefined);
  const [isUpdateStateFormOpen, setIsUpdateStateFormOpen] = useState(false);

  const RiskRoot = RiskStyles.RiskRoot;
  const { cardRoot, content, contentWrapper, header, panel } =
    RiskStyles.classesRisk;

  const geoStateUrl = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json';

  const allColors = ['rgb(0, 111, 162)', 'rgb(0, 185, 227)'];

  const fetchStats = useCallback(
    async (orgId?: string) => {
      const { result } = await apiPost<ApiResponse>('/stats', {
        body: {
          filters:
            (!orgId && showAllOrganizations) || !currentOrganization
              ? {}
              : orgId || 'rootDomains' in currentOrganization
              ? {
                  organization: orgId ? orgId : currentOrganization?.id
                }
              : { tag: currentOrganization.id }
        }
      });
      const max = Math.max(...result.vulnerabilities.byOrg.map((p) => p.value));
      colorScale = scaleLinear<string>()
        .domain([0, Math.log(max)])
        .range(['#c7e8ff', '#135787']);
      setStats(result);
    },
    [showAllOrganizations, apiPost, currentOrganization]
  );

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    if (user) {
      if (!user.state || user.state === '') {
        setIsUpdateStateFormOpen(true);
      }
    }
  }, [user]);

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
    <Paper elevation={0} className={cardRoot}>
      <div>
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
                          orgId: string;
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
                            if (cur) fetchStats(cur.orgId);
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
      </div>
    </Paper>
  );

  const latestVulnsGrouped: {
    [key: string]: VulnerabilityCount;
  } = {};
  if (stats) {
    for (const vuln of stats.vulnerabilities.latestVulnerabilities) {
      if (vuln.title in latestVulnsGrouped)
        latestVulnsGrouped[vuln.title].count++;
      else {
        latestVulnsGrouped[vuln.title] = { ...vuln, count: 1 };
      }
    }
  }

  const latestVulnsGroupedArr = Object.values(latestVulnsGrouped).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );

  if (stats) {
    for (const sev of severities) {
      sev.disable = !stats.domains.numVulnerabilities.some((i) =>
        sev.sevList.includes(i.id.split('|')[1])
      );
    }
  }

  if (isUpdateStateFormOpen) {
    return (
      <UpdateStateForm
        open={isUpdateStateFormOpen}
        userId={user?.id ?? ''}
        onClose={() => setIsUpdateStateFormOpen(false)}
      />
    );
  }

  if (user?.invitePending) {
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
              Thank you for requesting a Crossfeed account, you will receive
              notification once this request is approved.
            </Typography>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <RiskRoot className={classes.root}>
      <div id="wrapper" className={contentWrapper}>
        {stats && (
          <div className={content}>
            <div className={panel}>
              <VulnerabilityCard
                title={'Latest Vulnerabilities'}
                data={latestVulnsGroupedArr}
                showLatest={true}
                showCommon={false}
              ></VulnerabilityCard>
              {stats.domains.services.length > 0 && (
                <VulnerabilityPieChart
                  title={'Most Common Services'}
                  data={stats.domains.services}
                  colors={allColors}
                  type={'services'}
                />
              )}
              {stats.domains.ports.length > 0 && (
                <TopVulnerablePorts
                  data={stats.domains.ports.slice(0, 5).reverse()}
                />
              )}
              {stats.vulnerabilities.severity.length > 0 && (
                <VulnerabilityPieChart
                  title={'Severity Levels'}
                  data={stats.vulnerabilities.severity}
                  colors={getSeverityColor}
                  type={'vulns'}
                />
              )}
            </div>

            <div className={panel}>
              <Paper elevation={0} className={cardRoot}>
                <div>
                  {stats.domains.numVulnerabilities.length > 0 && (
                    <TopVulnerableDomains
                      data={stats.domains.numVulnerabilities}
                    />
                  )}
                </div>
              </Paper>

              <VulnerabilityCard
                title={'Most Common Vulnerabilities'}
                data={stats.vulnerabilities.mostCommonVulnerabilities}
                showLatest={false}
                showCommon={true}
              ></VulnerabilityCard>

              <div id="mapWrapper">
                {(user?.userType === 'globalView' ||
                  user?.userType === 'globalAdmin') &&
                  showMaps && (
                    <>
                      <MapCard
                        title={'State Vulnerabilities'}
                        geoUrl={geoStateUrl}
                        findFn={(geo) =>
                          stats?.vulnerabilities.byOrg.find(
                            (p) => p.label === geo.properties.name
                          )
                        }
                        type={'state'}
                      ></MapCard>
                      <MapCard
                        title={'County Vulnerabilities'}
                        geoUrl={geoStateUrl}
                        findFn={(geo) =>
                          stats?.vulnerabilities.byOrg.find(
                            (p) => p.label === geo.properties.name + ' Counties'
                          )
                        }
                        type={'county'}
                      ></MapCard>
                    </>
                  )}
              </div>
            </div>
          </div>
        )}
      </div>
    </RiskRoot>
  );
};

export default Risk;
