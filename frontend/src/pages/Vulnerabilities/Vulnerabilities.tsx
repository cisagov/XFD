import React, {
  useState,
  useCallback,
  useEffect,
  useMemo,
  useRef
} from 'react';
import { logger } from '@/utils/logger';
import { useHistory, useLocation } from 'react-router-dom';
import { differenceInCalendarDays, parseISO } from 'date-fns';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Checklist from '@mui/icons-material/Checklist';
import DynamicFeed from '@mui/icons-material/DynamicFeed';
import FiberManualRecordRounded from '@mui/icons-material/FiberManualRecordRounded';
import OpenInNew from '@mui/icons-material/OpenInNew';
import {
  DataGrid,
  getGridSingleSelectOperators,
  getGridStringOperators,
  GridColDef,
  GridColumnVisibilityModel,
  GridFilterModel,
  GridPaginationModel,
  GridRenderCellParams,
  GridSortModel
} from '@mui/x-data-grid';
import { useAuthContext } from 'context';
import { Query, UserOrganization } from 'types';
import { Vulnerability } from 'types/domain';
import {
  ApiResponse,
  LocationState,
  SearchParams,
  VulnerabilityRow
} from 'types/vulnerabilities';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import CustomNoRowsOverlay from 'components/DataGrid/CustomNoRowsOverlay';
import { FindingsHeader } from 'components/FindingsLibrary/FindingsHeader';
import { getSeverityColor } from 'utils/getSeverityColor';
import { truncateString } from 'utils/dataTransformUtils';
import {
  formatSeverity,
  normalizeFilters,
  extractInitialFilters,
  mapDisplayFieldToServerField
} from 'utils/vulnerabilitiesTableUtils';
import { ROUTES } from '@/constants/routes';
import { ENDPOINTS } from '@/constants/endpoints';

const PAGE_SIZE = 15;

interface VulnerabilitiesProps {
  group_by?: string;
}

const formatDays = (dateString: string) => {
  const date = parseISO(dateString);
  const days = differenceInCalendarDays(Date.now(), date);
  if (days <= 1) {
    return `${days} day ago`;
  }
  return `${days} days ago`;
};

export const Vulnerabilities: React.FC<VulnerabilitiesProps> = ({
  group_by
}) => {
  const { currentOrganization, apiPost, user } = useAuthContext();
  const history = useHistory();
  const location = useLocation();
  const state = location.state as LocationState;

  const [columnVisibilityModel, setColumnVisibilityModel] =
    useState<GridColumnVisibilityModel>({});
  const [filters, setFilters] = useState(() => extractInitialFilters(state));
  const [filterModel, setFilterModel] = useState<GridFilterModel>({
    items: []
  });
  const filterTimerRef = useRef<number | null>(null);
  const [hasPreloadedFilters, setPreloadedFiltersActive] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const lastFiltersKeyRef = useRef<string>(JSON.stringify(filters));
  const [loadingError, setLoadingError] = useState(false);
  const [onlyOpenVulns, setOnlyOpenVulns] = useState(true);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: PAGE_SIZE
  });
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [sortModel, setSortModel] = useState<GridSortModel>([
    {
      field: 'created_at',
      sort: 'desc'
    }
  ]);
  const sortField = sortModel[0]?.field;
  const sortFieldConversion =
    sortField === 'is_kev_display'
      ? 'is_kev'
      : sortField === 'is_kev_ransomware_display'
        ? 'is_kev_ransomware'
        : sortField;

  useEffect(() => {
    if (state) {
      const extracted = extractInitialFilters(state);
      setFilters(extracted);
      setPreloadedFiltersActive(extracted.length > 0);
    }
  }, [state]);

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
          currentOrganization
            ? ({
                ...currentOrganization,
                tags: currentOrganization.tags ?? []
              } as UserOrganization)
            : undefined,
          user?.user_type,
          state?.orgId
        );
        return await apiPost<ApiResponse>(
          doExport
            ? ENDPOINTS.VULNERABILITIES_EXPORT
            : ENDPOINTS.VULNERABILITIES_SEARCH,
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
        logger.error('Vulnerabilities search/export failed:', {
          error: e,
          page,
          pageSize,
          filters,
          showAll
        });
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
            pageSize: PAGE_SIZE
          }));
          setLoadingError(false);
          return;
        }
        setVulnerabilities(result);
        setTotalResults(count);
        setPaginationModel((prevState) => ({
          ...prevState,
          page: query.page - 1,
          pageSize: query.pageSize ?? PAGE_SIZE
        }));
        setLoadingError(false);
      } catch (e) {
        logger.error('Vulnerabilities.fetchVulnerabilities failed:', {
          error: e,
          page: query.page,
          pageSize: query.pageSize,
          group_by
        });
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
    setFilterModel({ items: [] });
    if (filterTimerRef.current) {
      clearTimeout(filterTimerRef.current);
      filterTimerRef.current = null;
    }
    setPaginationModel((prev) => ({
      ...prev,
      page: 0,
      pageSize: PAGE_SIZE
    }));
    fetchVulnerabilities({
      page: 1,
      pageSize: PAGE_SIZE,
      filters: [],
      order: mapDisplayFieldToServerField(sortModel[0]?.field),
      sort: sortModel[0]?.sort ?? 'desc',
      showAll: !onlyOpenVulns
    });
  }, [
    fetchVulnerabilities,
    history,
    location,
    sortFieldConversion,
    sortModel,
    onlyOpenVulns
  ]);

  useEffect(() => {
    fetchVulnerabilities({
      page: paginationModel.page + 1,
      pageSize: paginationModel.pageSize,
      order: mapDisplayFieldToServerField(sortModel[0]?.field),
      sort: sortModel[0]?.sort ?? 'desc',
      filters: filters || [],
      showAll: !onlyOpenVulns
    });
  }, [
    fetchVulnerabilities,
    filters,
    paginationModel.page,
    paginationModel.pageSize,
    onlyOpenVulns,
    sortFieldConversion,
    sortModel
  ]);

  useEffect(() => {
    return () => {
      if (filterTimerRef.current) {
        clearTimeout(filterTimerRef.current);
        filterTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    lastFiltersKeyRef.current = JSON.stringify(filters);
  }, [filters]);

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

        const kevStatus =
          vuln.is_kev === null ? 'N/A' : vuln.is_kev ? 'Yes' : 'No';

        const ransomwareStatus =
          vuln?.is_kev_ransomware === null
            ? 'N/A'
            : vuln.is_kev_ransomware
              ? 'Yes'
              : 'No';

        return {
          id: vuln.id,
          title: vuln.title,
          severity: severity,
          is_kev: typeof vuln.is_kev === 'boolean' ? vuln.is_kev : null, // Keep original boolean data
          is_kev_display: kevStatus, // Add display version
          is_kev_ransomware:
            typeof vuln.is_kev_ransomware === 'boolean'
              ? vuln.is_kev_ransomware
              : null, // Keep original boolean data
          is_kev_ransomware_display: ransomwareStatus, // Add display version
          domain: vuln.domain?.name,
          domainId: vuln.domain?.id,
          product: product,
          created_at: daysOpen,
          state: stateDisplay
        };
      }),
    [vulnerabilities]
  );

  const stringFilterOperators = useMemo(() => {
    try {
      const operators = getGridStringOperators();
      const allowedOperators = ['contains', 'equals'];
      return operators.filter((op) =>
        allowedOperators.includes(op.value as string)
      );
    } catch {
      return [
        { label: 'Contains', value: 'contains' } as any,
        { label: 'Equals', value: 'equals' } as any
      ];
    }
  }, []);

  const vulCols: GridColDef<VulnerabilityRow>[] = useMemo(
    () => [
      {
        field: 'title',
        headerName: 'Vulnerability',
        minWidth: 100,
        flex: 2,
        filterOperators: stringFilterOperators,
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
        filterOperators: stringFilterOperators,
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
        field: 'is_kev_display',
        headerName: 'KEV',
        minWidth: 50,
        flex: 0.3,
        type: 'singleSelect',
        valueOptions: [
          { value: 'Yes', label: 'Yes' },
          { value: 'No', label: 'No' },
          { value: 'N/A', label: 'N/A' }
        ],
        filterOperators: getGridSingleSelectOperators().filter(
          (op) => op.value === 'is'
        ),
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          const v = cellValues.row.is_kev_display;
          return (
            <Box component="span" aria-label={`KEV status ${v}`}>
              {v}
            </Box>
          );
        }
      },
      {
        field: 'is_kev_ransomware_display',
        headerName: 'Ransomware',
        minWidth: 100,
        flex: 0.5,
        filterable: true,
        filterOperators: getGridSingleSelectOperators().filter(
          (op) => op.value === 'is'
        ),
        type: 'singleSelect',
        valueOptions: [
          { value: 'Yes', label: 'Yes' },
          { value: 'No', label: 'No' },
          { value: 'N/A', label: 'N/A' }
        ],
        renderCell: (cellValues: GridRenderCellParams<VulnerabilityRow>) => {
          const v = cellValues.row.is_kev_ransomware_display;
          return (
            <Box component="span" aria-label={`Ransomware status ${v}`}>
              {v}
            </Box>
          );
        }
      },
      {
        field: 'domain',
        headerName: 'Domain',
        minWidth: 100,
        flex: 1,
        filterOperators: stringFilterOperators,
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
        filterOperators: stringFilterOperators,
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
        filterOperators: stringFilterOperators,
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
        filterOperators: stringFilterOperators,
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
                history.push(
                  ROUTES.VULNERABILITY.replace(
                    ':vulnerabilityId',
                    String(cellValues.row.id)
                  )
                )
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
              onClick={() => {
                fetchVulnerabilities({
                  page: paginationModel.page + 1,
                  pageSize: paginationModel.pageSize,
                  order: mapDisplayFieldToServerField(sortModel[0]?.field),
                  sort: sortModel[0]?.sort ?? 'desc',
                  filters: filters,
                  showAll: !onlyOpenVulns
                });
              }}
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
            <DataGrid<VulnerabilityRow>
              rows={vulRows}
              rowCount={totalResults}
              columns={vulCols}
              loading={isLoading}
              columnVisibilityModel={columnVisibilityModel}
              onColumnVisibilityModelChange={(model) =>
                setColumnVisibilityModel(model)
              }
              filterMode="server"
              filterModel={filterModel}
              onFilterModelChange={(model) => {
                const mappedItems = model.items.map((item) => ({
                  ...item,
                  value:
                    typeof item.value === 'string'
                      ? item.value.trim()
                      : item.value
                }));
                const normalizedModel = { ...model, items: mappedItems };
                setFilterModel(normalizedModel);

                const mappedFilters = normalizedModel.items
                  .map((item) => {
                    let val: any = item.value;
                    if (
                      item.field === 'is_kev' ||
                      item.field === 'is_kev_ransomware'
                    ) {
                      if (typeof val === 'string') {
                        const v = val.toLowerCase();
                        if (v === 'yes' || v === 'true') val = true;
                        else if (v === 'no' || v === 'false') val = false;
                        else if (v === 'n/a') val = null;
                        else val = null;
                      } else {
                        val = val == null ? null : Boolean(val);
                      }
                    }
                    return {
                      field: item.field,
                      operator: item.operator,
                      value: val
                    };
                  })

                  .filter(
                    (f) =>
                      f.value !== undefined &&
                      f.value !== null &&
                      !(typeof f.value === 'string' && f.value.trim() === '')
                  );

                const mappedKey = JSON.stringify(mappedFilters);

                if (mappedKey === lastFiltersKeyRef.current) {
                  return;
                }
                if (filterTimerRef.current) {
                  clearTimeout(filterTimerRef.current);
                }
                filterTimerRef.current = window.setTimeout(() => {
                  setIsLoading(true);
                  setFilters(mappedFilters);
                  lastFiltersKeyRef.current = mappedKey;
                  setPaginationModel((prev) => ({ ...prev, page: 0 }));
                  filterTimerRef.current = null;
                }, 1000);
              }}
              paginationMode="server"
              paginationModel={paginationModel}
              onPaginationModelChange={(model) => {
                setPaginationModel((prev) => ({
                  ...prev,
                  page: model.page,
                  pageSize: model.pageSize
                }));
              }}
              pageSizeOptions={[15, 30, 50, 100]}
              sortModel={sortModel}
              sortingMode="server"
              onSortModelChange={(model) => {
                setSortModel(model);
                setPaginationModel((prev) => ({ ...prev, page: 0 }));
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
                },
                columnsManagement: {
                  disableResetButton: true,
                  getTogglableColumns: (columns) => {
                    const alwaysVisible = ['title'];
                    return columns
                      .filter(
                        (col) => col.field && !alwaysVisible.includes(col.field)
                      )
                      .map((col) => col.field as string);
                  }
                }
              }}
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
