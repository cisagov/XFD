import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { Link as RouterLink, useHistory, useLocation } from 'react-router-dom';
import { Query } from 'types';
import { useAuthContext } from 'context';
import {
  Alert,
  Box,
  Button,
  Divider,
  IconButton,
  Link,
  Paper,
  Stack,
  Typography
} from '@mui/material';
import {
  DataGrid,
  GridColDef,
  GridPaginationModel,
  GridRenderCellParams
} from '@mui/x-data-grid';
import {
  Checklist,
  DynamicFeed,
  FiberManualRecordRounded,
  OpenInNew
} from '@mui/icons-material';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import CustomNoRowsOverlay from 'components/DataGrid/CustomNoRowsOverlay';
import { getSeverityColor } from 'pages/Risk/utils';
import { differenceInCalendarDays, parseISO } from 'date-fns';
import { truncateString } from 'utils/dataTransformUtils';
import { Vulnerability } from 'types/domain';
import {
  ApiResponse,
  LocationState,
  SearchParams,
  VulnerabilityRow
} from 'types/vulnerabilities';
import { formatSeverity } from 'utils/vulnerabilitiesTableUtils';
import { normalizeFilters } from 'utils/vulnerabilitiesTableUtils';
import { FindingsHeader } from 'components/FindingsLibrary/FindingsHeader';
import { extractInitialFilters } from 'utils/vulnerabilitiesTableUtils';

const PAGE_SIZE = 15;

interface VulnerabilitiesProps {
  group_by?: string;
}

export const Vulnerabilities: React.FC<VulnerabilitiesProps> = ({
  group_by
}) => {
  const { currentOrganization, apiPost, user } = useAuthContext();
  const history = useHistory();
  const location = useLocation();
  const state = location.state as LocationState;
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [loadingError, setLoadingError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [onlyOpenVulns, setOnlyOpenVulns] = useState(true);
  const [initialFilters, setInitialFilters] = useState(() =>
    extractInitialFilters(state)
  );

  const filters = initialFilters.length > 0 ? initialFilters : [];

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: PAGE_SIZE,
    pageCount: 0,
    filters: filters
  });

  const vulnerabilitiesSearch = useCallback(
    async ({
      filters,
      page,
      pageSize = PAGE_SIZE,
      doExport = false,
      group_by,
      showAll = false
    }: SearchParams): Promise<ApiResponse | undefined> => {
      try {
        const tableFilters = normalizeFilters(
          filters,
          currentOrganization,
          user?.user_type,
          state?.orgId
        );
        return await apiPost<ApiResponse>(
          doExport ? '/vulnerabilities/export' : '/vulnerabilities/search',
          {
            body: { page, filters: tableFilters, pageSize, group_by, showAll }
          }
        );
      } catch (e) {
        console.error(e);
        setLoadingError(true);
        return;
      }
    },
    [apiPost, currentOrganization, user?.user_type, state?.orgId]
  );

  const fetchVulnerabilities = useCallback(
    async (query: Query<Vulnerability>) => {
      setIsLoading(true);
      setLoadingError(false);
      try {
        const resp = await vulnerabilitiesSearch({
          filters: query.filters,
          page: query.page,
          pageSize: query.pageSize ?? PAGE_SIZE,
          group_by,
          showAll: query.showAll
        });
        if (!resp) return;
        const { result, count } = resp;
        if (result.length === 0) {
          setVulnerabilities([]);
          setTotalResults(0);
          setPaginationModel((prevState) => ({
            ...prevState,
            page: 0,
            pageSize: PAGE_SIZE,
            pageCount: 0,
            filters: []
          }));
          setLoadingError(false);
          return;
        }
        setVulnerabilities(result);
        setTotalResults(count);
        setPaginationModel((prevState) => ({
          ...prevState,
          page: query.page - 1,
          pageSize: query.pageSize ?? PAGE_SIZE,
          pageCount: Math.ceil(count / (query.pageSize ?? PAGE_SIZE)),
          filters: query.filters
        }));
        setLoadingError(false);
      } catch (e) {
        console.error(e);
        setLoadingError(true);
      } finally {
        setIsLoading(false);
      }
    },
    [vulnerabilitiesSearch, group_by]
  );

  const resetVulnerabilities = useCallback(() => {
    setInitialFilters([]);
    fetchVulnerabilities({
      page: 1,
      pageSize: PAGE_SIZE,
      filters: []
    });
  }, [fetchVulnerabilities]);

  useEffect(() => {
    fetchVulnerabilities({
      page: paginationModel.page + 1,
      pageSize: paginationModel.pageSize,
      filters: initialFilters || [],
      showAll: !onlyOpenVulns
    });
  }, [
    fetchVulnerabilities,
    paginationModel.page,
    paginationModel.pageSize,
    initialFilters,
    onlyOpenVulns
  ]);

  const handlePaginationModelChange = useCallback(
    (model: GridPaginationModel) => {
      setPaginationModel((prev) => ({
        ...prev,
        page: model.page,
        pageSize: model.pageSize
      }));
    },
    []
  );
  const showAllVulnsButton = (
    <Button
      size="small"
      sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
      startIcon={<DynamicFeed />}
      onClick={() => {
        setOnlyOpenVulns(false);
        // fetchVulnerabilities will be triggered by useEffect due to onlyOpenVulns change
      }}
    >
      Show All Vulnerabilities
    </Button>
  );

  const showOpenVulnsButton = (
    <Button
      size="small"
      sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
      startIcon={<Checklist />}
      onClick={() => {
        setOnlyOpenVulns(true);
        // fetchVulnerabilities will be triggered by useEffect due to onlyOpenVulns change
      }}
    >
      Show Open Vulnerabilities
    </Button>
  );

  const noRowsOverlay = (
    <Box>
      <Stack direction="row" alignItems="center" spacing={2}>
        <Paper elevation={1}>
          <Alert severity="warning">
            No Results Found. Please adjust your filters.
          </Alert>
        </Paper>
      </Stack>
    </Box>
  );

  const vulRows: VulnerabilityRow[] = useMemo(
    () =>
      vulnerabilities.map((vuln) => {
        const severity = formatSeverity(vuln.severity ?? 'N/A');

        const product = vuln.cpe
          ? vuln.cpe
          : vuln.service?.products?.[0]?.cpe || 'N/A';

        const daysOpen = vuln?.created_at
          ? `${differenceInCalendarDays(Date.now(), parseISO(vuln?.created_at))} days`
          : '';

        const stateDisplay =
          vuln.state + (vuln.substate ? ` (${vuln.substate})` : '');

        return {
          id: vuln.id,
          title: vuln.title,
          severity: severity,
          kev: vuln.is_kev ? 'Yes' : 'No',
          domain: vuln.domain?.name,
          domainId: vuln.domain?.id,
          product: product,
          created_at: daysOpen,
          state: stateDisplay
        };
      }),
    [vulnerabilities]
  );

  const vulCols: GridColDef<VulnerabilityRow>[] = useMemo(
    () => [
      {
        field: 'title',
        headerName: 'Vulnerability',
        minWidth: 100,
        flex: 2,
        sortComparator: (v1: any, v2: any) => {
          const collator = new Intl.Collator(undefined, {
            numeric: true,
            sensitivity: 'base'
          });
          return collator.compare(String(v1), String(v2));
        },
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          if (cellValues.row.title && cellValues.row.title.startsWith('CVE')) {
            return (
              <Link
                component={RouterLink}
                to={`/inventory/vulnerability/${cellValues.row.id}`}
                aria-label={`View NIST entry for ${cellValues.row.title}`}
                tabIndex={cellValues.tabIndex}
              >
                {cellValues.row.title}
              </Link>
            );
          }
          return (
            <Typography variant="body2" pl={1}>
              {truncateString(cellValues.row.title ?? '')}
            </Typography>
          );
        }
      },
      {
        field: 'severity',
        headerName: 'Severity',
        minWidth: 100,
        flex: 0.7,
        sortComparator: (v1: any, v2: any) => {
          const severityLevels: Record<string, number> = {
            'N/A': 1,
            Low: 2,
            Medium: 3,
            High: 4,
            Critical: 5,
            Other: 6
          };
          return severityLevels[String(v1)] - severityLevels[String(v2)];
        },
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          const severityText = cellValues.row.severity;
          const severityColor = getSeverityColor({ id: severityText || '' });
          return (
            <Stack>
              <div>{severityText}</div>
              <Box
                sx={{
                  height: '.5em',
                  width: '5em',
                  backgroundColor: severityColor
                }}
              />
            </Stack>
          );
        }
      },
      {
        field: 'kev',
        headerName: 'KEV',
        minWidth: 50,
        flex: 0.3
      },
      {
        field: 'domain',
        headerName: 'Domain',
        minWidth: 100,
        flex: 1,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          return (
            <Link
              component={RouterLink}
              to={`/inventory/domain/${cellValues.row.domainId}`}
              aria-label={`View details for ${cellValues.row.domain}`}
              tabIndex={cellValues.tabIndex}
            >
              {cellValues.row.domain}
            </Link>
          );
        }
      },
      {
        field: 'product',
        headerName: 'Product',
        minWidth: 100,
        flex: 1
      },
      {
        field: 'created_at',
        headerName: 'Days Open',
        minWidth: 100,
        flex: 0.5
      },
      {
        field: 'state',
        headerName: 'Status',
        minWidth: 100,
        flex: 1
      },
      {
        field: 'viewDetails',
        headerName: 'Details',
        minWidth: 75,
        flex: 0.5,
        disableExport: true,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          return (
            <IconButton
              aria-label={`View details for ${cellValues.row.title}`}
              tabIndex={cellValues.tabIndex}
              color="primary"
              onClick={() =>
                history.push(`/inventory/vulnerability/${cellValues.row.id}`)
              }
            >
              <OpenInNew />
            </IconButton>
          );
        }
      }
    ],
    [history]
  );

  return (
    <FindingsHeader>
      {!isLoading && !loadingError && filters.length > 0 && (
        <Box sx={{ width: '100%', mb: 1 }}>
          <Stack direction="row" alignItems="center">
            <FiberManualRecordRounded sx={{ color: 'primary.main' }} />
            <Typography variant="body1" color="neutrals.main">
              &nbsp;Filters Applied:
            </Typography>
            {state.orgName ? (
              <Typography variant="body1" color="neutrals.main" ml={1}>
                <b>Organization</b> - {state.orgName}
              </Typography>
            ) : (
              ''
            )}
            {state.title ? (
              <Typography variant="body1" color="neutrals.main" ml={1}>
                <b>Vulnerability</b> - {state.title}
              </Typography>
            ) : (
              ''
            )}
            {state.domain ? (
              <Typography variant="body1" color="neutrals.main" ml={1}>
                <b>Domain</b> - {state.domain}
              </Typography>
            ) : (
              ''
            )}
            {state.kev ? (
              <Typography variant="body1" color="neutrals.main" ml={1}>
                <b>KEV</b> - Yes
              </Typography>
            ) : (
              ''
            )}
            {state.severity ? (
              <Typography variant="body1" color="neutrals.main" ml={1}>
                <b>Severity</b> -{' '}
                {state.severity.charAt(0).toUpperCase() +
                  state.severity.slice(1)}
              </Typography>
            ) : (
              ''
            )}
            {state.dateRange ? (
              <Typography variant="body1" color="neutrals.main" ml={1}>
                <b>Scan Date</b> - {state.dateRange}
              </Typography>
            ) : (
              ''
            )}
            &nbsp;&nbsp;&nbsp;
            <Divider
              orientation="vertical"
              flexItem
              variant="middle"
              sx={{
                height: 24,
                alignSelf: 'center',
                borderColor: 'neutrals.light',
                ml: 2
              }}
            />
            <Button
              variant="text"
              onClick={resetVulnerabilities}
              sx={{
                color: 'primary.dark',
                fontSize: '14px',
                letterSpacing: '3px',
                ml: 2
              }}
            >
              Reset
            </Button>
          </Stack>
        </Box>
      )}
      <Box mb={3} display="flex" justifyContent="center">
        {isLoading ? (
          <Paper elevation={2}>
            <Alert severity="info">Loading Vulnerabilities..</Alert>
          </Paper>
        ) : isLoading === false && loadingError === true ? (
          <Stack direction="row" spacing={2}>
            <Paper elevation={2}>
              <Alert severity="warning">Error Loading Vulnerabilities!</Alert>
            </Paper>
            <Button
              onClick={resetVulnerabilities}
              variant="contained"
              color="primary"
              sx={{ width: 'fit-content' }}
            >
              Retry
            </Button>
          </Stack>
        ) : isLoading === false && loadingError === false ? (
          <Paper elevation={2} sx={{ width: '100%', minHeight: 500 }}>
            <DataGrid
              rows={vulRows}
              rowCount={totalResults}
              columns={vulCols}
              loading={isLoading}
              slots={{
                toolbar: CustomToolbar,
                noRowsOverlay: CustomNoRowsOverlay
              }}
              slotProps={{
                toolbar: {
                  children: onlyOpenVulns
                    ? showAllVulnsButton
                    : showOpenVulnsButton,
                  exportTitle: 'Vulnerabilities'
                } as any,
                noRowsOverlay: { children: noRowsOverlay }
              }}
              paginationMode="server"
              paginationModel={paginationModel}
              onPaginationModelChange={handlePaginationModelChange}
              pageSizeOptions={[15, 30, 50, 100]}
            />
          </Paper>
        ) : null}
      </Box>
    </FindingsHeader>
  );
};

export default Vulnerabilities;
