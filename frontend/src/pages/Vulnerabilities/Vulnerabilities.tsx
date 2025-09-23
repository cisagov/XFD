import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import { Query } from 'types';
import { useAuthContext } from 'context';
import {
  Alert,
  Box,
  Button,
  Divider,
  IconButton,
  Paper,
  Stack,
  Typography
} from '@mui/material';
import {
  DataGrid,
  GridColDef,
  GridPaginationModel,
  GridRenderCellParams,
  GridSortModel
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
  const [sortModel, setSortModel] = useState<GridSortModel>([
    {
      field: 'created_at',
      sort: 'desc'
    }
  ]);
  const [filters, setFilters] = useState(() => extractInitialFilters(state));
  const [hasPreloadedFilters, setPreloadedFiltersActive] = useState(false);

  useEffect(() => {
    if (state) {
      const extracted = extractInitialFilters(state);
      setFilters(extracted);
      setPreloadedFiltersActive(extracted.length > 0);
    }
  }, [state]);

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
      order,
      sort,
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
            body: {
              page,
              filters: tableFilters,
              pageSize,
              group_by,
              showAll,
              order,
              sort
            }
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
          order: query.order,
          sort: query.sort,
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
    history.replace({ ...location, state: null });
    setPreloadedFiltersActive(false);
    setFilters([]);
    setPaginationModel((prev) => ({
      ...prev,
      page: 0,
      filters: []
    }));
    fetchVulnerabilities({
      page: 1,
      pageSize: PAGE_SIZE,
      filters: []
    });
  }, [fetchVulnerabilities, history, location]);

  useEffect(() => {
    fetchVulnerabilities({
      page: paginationModel.page + 1,
      pageSize: paginationModel.pageSize,
      order: sortModel[0]?.field,
      sort: sortModel[0]?.sort ?? 'desc',
      filters: filters || [],
      showAll: !onlyOpenVulns
    });
  }, [
    fetchVulnerabilities,
    paginationModel.page,
    paginationModel.pageSize,
    sortModel,
    filters,
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
      }}
    >
      Include Closed Vulnerabilities
    </Button>
  );

  const showOpenVulnsButton = (
    <Button
      size="small"
      sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
      startIcon={<Checklist />}
      onClick={() => {
        setOnlyOpenVulns(true);
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

  const formatDays = (dateString: string) => {
    const date = parseISO(dateString);
    const days = differenceInCalendarDays(Date.now(), date);
    if (days <= 1) {
      return `${days} day ago`;
    }
    return `${days} days ago`;
  };
  const vulRows: VulnerabilityRow[] = useMemo(
    () =>
      vulnerabilities.map((vuln) => {
        const severity = formatSeverity(vuln.severity ?? 'N/A');

        const product = vuln.cpe
          ? vuln.cpe
          : vuln.service?.products?.[0]?.cpe || 'N/A';

        const daysOpen = vuln?.created_at ? formatDays(vuln?.created_at) : '';

        const stateDisplay =
          vuln.state + (vuln.substate ? ` (${vuln.substate})` : '');

        return {
          id: vuln.id,
          title: vuln.title,
          severity: severity,
          is_kev: vuln.is_kev ? 'Yes' : 'No',
          is_kev_ransomware: vuln.is_kev_ransomware ? 'Yes' : 'No',
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
          return (
            <Box
              component="span"
              aria-label={`Vulnerability ${cellValues.row.title}`}
            >
              {truncateString(cellValues.row.title ?? '')}
            </Box>
          );
        }
      },
      {
        field: 'severity',
        headerName: 'Severity',
        minWidth: 100,
        flex: 0.5,
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
            <Box
              component="span"
              sx={{
                borderBottom: `4px solid ${severityColor}`,
                display: 'inline-block',
                lineHeight: 1,
                pb: '2px'
              }}
              aria-label={`Severity ${severityText}`}
            >
              {severityText}
            </Box>
          );
        }
      },
      {
        field: 'is_kev',
        headerName: 'KEV',
        minWidth: 50,
        flex: 0.3,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          return (
            <Box
              component="span"
              aria-label={`KEV status ${cellValues.row.is_kev}`}
            >
              {cellValues.row.is_kev}
            </Box>
          );
        }
      },
      {
        field: 'is_kev_ransomware',
        headerName: 'Ransomware',
        minWidth: 100,
        flex: 0.5,
        filterable: true,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => (
          <Box
            component="span"
            aria-label={`Ransomware status ${cellValues.row.is_kev_ransomware}`}
          >
            {cellValues.row.is_kev_ransomware}
          </Box>
        )
      },
      {
        field: 'domain',
        headerName: 'Domain',
        minWidth: 100,
        flex: 1,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          return (
            <Box
              component="span"
              aria-label={`Domain address ${cellValues.row.domain}`}
              tabIndex={cellValues.tabIndex}
            >
              {cellValues.row.domain}
            </Box>
          );
        }
      },
      {
        field: 'product',
        headerName: 'Product',
        minWidth: 100,
        flex: 1,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          return (
            <Box
              component="span"
              aria-label={`Product ${cellValues.row.product}`}
            >
              {cellValues.row.product}
            </Box>
          );
        }
      },
      {
        field: 'created_at',
        headerName: 'Days Open',
        minWidth: 100,
        flex: 0.5,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          return (
            <Box
              component="span"
              aria-label={`${cellValues.row.created_at} open`}
            >
              {cellValues.row.created_at}
            </Box>
          );
        }
      },
      {
        field: 'state',
        headerName: 'Status',
        minWidth: 100,
        flex: 1,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          return (
            <Box
              component="span"
              aria-label={`Vulnerability status ${cellValues.row.state}`}
            >
              {cellValues.row.state}
            </Box>
          );
        }
      },
      {
        field: 'viewDetails',
        headerName: 'Details',
        minWidth: 75,
        flex: 0.5,
        disableExport: true,
        filterable: false,
        sortable: false,
        disableColumnMenu: true,
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          return (
            <IconButton
              aria-label={`Vulnerability details for ${cellValues.row.title}`}
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
    <Box
      display="flex"
      flexDirection="column"
      minHeight="100vh"
      maxWidth="1152px"
      width="100%"
      margin="auto"
    >
      <FindingsHeader />
      {!isLoading && !loadingError && state && hasPreloadedFilters && (
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
                fontWeight: 'bold',
                lineHeight: '20px',
                letterSpacing: '0.1em',
                ml: 1
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
          <Paper
            elevation={2}
            sx={{ width: '100%', minHeight: 500 }}
            aria-label="Vulnerabilities Table"
          >
            <DataGrid
              rows={vulRows}
              rowCount={totalResults}
              columns={vulCols}
              loading={isLoading}
              sortModel={sortModel}
              sortingMode="server"
              onSortModelChange={(model) => {
                setSortModel(model);
              }}
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
                noRowsOverlay: { children: noRowsOverlay },
                basePopper: {
                  placement: 'bottom-start'
                }
              }}
              paginationMode="server"
              paginationModel={paginationModel}
              onPaginationModelChange={handlePaginationModelChange}
              pageSizeOptions={[15, 30, 50, 100]}
              disableRowSelectionOnClick
              showToolbar
            />
          </Paper>
        ) : null}
      </Box>
    </Box>
  );
};

export default Vulnerabilities;
