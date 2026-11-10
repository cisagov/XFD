// React
import React, { useCallback, useEffect, useRef, useState } from 'react';

// Material-UI Components
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import MuiButton from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import KeyboardArrowDown from '@mui/icons-material/KeyboardArrowDown';
import type {
  GridColDef,
  GridFilterModel,
  GridRenderCellParams
} from '@mui/x-data-grid';

// Material-UI Icons
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import RefreshIcon from '@mui/icons-material/Refresh';

// Node Packages
// @ts-ignore:next-line
import { formatDistanceToNow, parseISO } from 'date-fns';

// Components
import CustomDataGrid from '@/components/DataGrid/CustomDataGrid';
import CustomToolbar from '@/components/DataGrid/CustomToolbar';
import CustomPagination from '@/components/DataGrid/CustomPagination';

// Constants
import { ENDPOINTS } from '@/constants/endpoints';

// Context
import { useAuthContext } from '@/context';

// Types
import { OrgQuery, Scan, ScanTask } from '@/types';

// Constants & Utils
import {
  DATA_GRID_PAGE_SIZE_OPTIONS,
  DEFAULT_DATA_GRID_PAGE_SIZE,
  SERVER_FILTER_DEBOUNCE_MS
} from '@/constants/dataGrid';
import { logger } from '@/utils/logger';
import { textFilterOperators } from '@/utils/transformTableData';
import { cleanFilterModelItems, isFilterModelEmpty } from '@/utils/tableUtils';

// Third Party libraries
import { LazyLog as MellowareLazyLog } from '@melloware/react-logviewer';

interface ApiResponse {
  result: ScanTask[];
  count: number;
}

interface Errors {
  global?: string;
}

export interface ScansTaskRow {
  id: string;
  status: string;
  name: string;
  input: string;
  output: string;
  created_at: string;
  started_at: string;
  requested_at: string;
  finished_at: string;
  scan: Scan;
  fargate_task_arn: string;
}

const dateAccessor = (date?: string) => {
  return !date || new Date(date).getTime() === new Date(0).getTime()
    ? 'None'
    : `${formatDistanceToNow(parseISO(date))} ago`;
};

const Log = ({ url, token }: { url: string; token: string }) => {
  const [logKey, setLogKey] = useState(0);
  return (
    <Box sx={{ position: 'relative', width: '100%', height: '60vh' }}>
      <MellowareLazyLog
        aria-label="Log readout"
        key={'lazylog-' + logKey}
        follow={true}
        extraLines={1}
        enableSearch
        url={url}
        caseInsensitive
        fetchOptions={{ headers: { Authorization: token } }}
        selectableLines={true}
      />
      <IconButton
        aria-label="Refresh log"
        size="small"
        sx={{
          backgroundColor: 'neutrals.white',
          '&:hover': { backgroundColor: 'neutrals.light' },
          position: 'absolute',
          bottom: '25px',
          right: '20px'
        }}
        onClick={() => setLogKey(Math.random())}
      >
        <RefreshIcon />
      </IconButton>
    </Box>
  );
};

export const ScanTasksView: React.FC = () => {
  const { apiPost, token, currentOrganization, showAllOrganizations } =
    useAuthContext();
  const [scanTasks, setScanTasks] = useState<ScanTask[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [errors, setErrors] = useState<Errors>({});

  const [openDialog, setOpenDialog] = useState(false);
  const [detailsParams, setDetailsParams] = useState<GridRenderCellParams>();

  const killScanTask2 = async (id: string) => {
    try {
      await apiPost(ENDPOINTS.SCAN_TASKS_KILL.replace('{scan_task_id}', id), {
        body: {}
      });
      const index = scanTasks.findIndex((task) => task.id === id);
      setScanTasks(
        Object.assign([], scanTasks, {
          [index]: {
            ...scanTasks[index],
            status: 'failed'
          }
        })
      );
    } catch (e: any) {
      setErrors({
        global:
          e.status === 422 ? 'Unable to kill scan' : (e.message ?? e.toString())
      });
      logger.error('ScanTasksView.killScanTask failed:', {
        error: e,
        scanTaskId: id
      });
    }
  };

  const filterTimerRef = useRef<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [filterModel, setFilterModel] = useState<GridFilterModel>({
    items: []
  });
  const [hasActiveFilters, setHasActiveFilters] = useState(false);
  const requestIdRef = useRef(0);
  const fetchScanTasks = useCallback(
    async (query: OrgQuery<ScanTask>) => {
      const { page, sort, filters } = query;
      setIsLoading(true);
      setErrors({});
      const requestId = ++requestIdRef.current;
      try {
        if (requestId !== requestIdRef.current) return;
        const tableFilters: {
          [key: string]: string | boolean | undefined;
        } = filters
          .filter((f) => Boolean(f.value))
          .reduce(
            (accum, next) => ({
              ...accum,
              [next.id]: next.value
            }),
            {}
          );
        // We only want to be able to filter with the dropdown org/tag bar
        if (!showAllOrganizations && currentOrganization) {
          if ('root_domains' in currentOrganization)
            tableFilters['organization'] = currentOrganization.id;
          else tableFilters['tag'] = currentOrganization.id;
        }
        const { result, count } = await apiPost<ApiResponse>(
          ENDPOINTS.SCANS_TASK_SEARCH,
          {
            body: {
              page,
              pageSize: query.pageSize ?? DEFAULT_DATA_GRID_PAGE_SIZE,
              sort: sort[0]?.id ?? 'created_at',
              order: 'DESC',
              filters: tableFilters
            }
          }
        );
        // if (result.length === 0) return;
        setScanTasks(result);
        setTotalResults(count);
        setPaginationModel((prev) => ({
          ...prev,
          page: query.page - 1,
          pageSize: query.pageSize ?? DEFAULT_DATA_GRID_PAGE_SIZE,
          pageCount: Math.ceil(
            count / (query.pageSize ?? DEFAULT_DATA_GRID_PAGE_SIZE)
          )
        }));
      } catch (e) {
        setErrors({ global: 'Failed to fetch scan task data.' });
        logger.error('ScanTasksView.fetchScanTasks failed:', {
          error: e,
          page: query.page,
          filters: query.filters
        });
      } finally {
        if (requestId === requestIdRef.current) {
          setIsLoading(false);
        }
      }
    },
    [apiPost, currentOrganization, showAllOrganizations]
  );

  //New Table for Scans

  const scansTasksRows: ScansTaskRow[] = scanTasks.map((scanTask) => ({
    id: scanTask.id,
    status: scanTask.status,
    name: `${scanTask.scan?.name ?? 'None'}-${scanTask.concurrency_index ?? 1}`,
    input: scanTask.input,
    output: scanTask.output,
    created_at: dateAccessor(scanTask.created_at),
    started_at: dateAccessor(scanTask.started_at),
    requested_at: scanTask.requested_at,
    finished_at: dateAccessor(scanTask.finished_at),
    scan: scanTask.scan,
    fargate_task_arn: scanTask.fargate_task_arn
  }));

  const scansTasksCols: GridColDef[] = [
    {
      field: 'id',
      filterable: false,
      headerName: 'ID',
      minWidth: 150,
      flex: 2,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Scan Task ID: ${cellValues.row.id}`}
          >
            {cellValues.row.id}
          </Box>
        );
      }
    },
    {
      field: 'status',
      headerName: 'Status',
      minWidth: 100,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Status for Scan Task ${cellValues.row.id}: ${cellValues.row.status}`}
          >
            {cellValues.row.status}
          </Box>
        );
      }
    },
    {
      field: 'name',
      headerName: 'Name',
      minWidth: 150,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Name for Scan Task ${cellValues.row.id}: ${cellValues.row.name}`}
          >
            {cellValues.row.name}
          </Box>
        );
      }
    },
    {
      field: 'created_at',
      headerName: 'Created At',
      minWidth: 150,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Created At Date for Scan Task ${cellValues.row.id}: ${cellValues.row.created_at}`}
          >
            {cellValues.row.created_at}
          </Box>
        );
      }
    },
    {
      field: 'finished_at',
      headerName: 'Finished At',
      minWidth: 150,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Finished At Date for Scan Task ${cellValues.row.id}: ${cellValues.row.finished_at}`}
          >
            {cellValues.row.finished_at}
          </Box>
        );
      }
    },
    {
      field: 'details',
      headerName: 'Details',
      minWidth: 50,
      flex: 0.5,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            aria-label={`View Details for scan task ${cellValues.row.id}`}
            tabIndex={cellValues.tabIndex}
            color="primary"
            onClick={() => {
              setOpenDialog(true);
              setDetailsParams(cellValues);
            }}
          >
            <InfoOutlinedIcon />
          </IconButton>
        );
      }
    }
  ];

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: DEFAULT_DATA_GRID_PAGE_SIZE,
    sort: [],
    filters: [] as { id: string; value: any }[]
  });

  useEffect(() => {
    fetchScanTasks({
      page: 1,
      pageSize: paginationModel.pageSize,
      sort: paginationModel.sort,
      filters: paginationModel.filters
    });
  }, [fetchScanTasks, paginationModel.sort, paginationModel.filters]);

  useEffect(() => {
    return () => {
      if (filterTimerRef.current) {
        clearTimeout(filterTimerRef.current);
        filterTimerRef.current = null;
      }
    };
  }, []);

  const [anchorElName, setAnchorElName] = useState<null | HTMLElement>(null);
  const [anchorElStatus, setAnchorElStatus] = useState<null | HTMLElement>(
    null
  );
  const openNameMenu = Boolean(anchorElName);
  const openStatusMenu = Boolean(anchorElStatus);
  const [selectedName, setSelectedName] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const handleStatusClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElStatus(event.currentTarget);
  };
  const handleNameClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElName(event.currentTarget);
  };

  const handleNameSelect = (name: string) => {
    setPaginationModel((prev) => ({
      ...prev,
      filters: [
        ...prev.filters.filter((f) => f.id !== 'name'),
        { id: 'name', value: name }
      ]
    }));
    setAnchorElName(null);
    setSelectedName(name);
    setHasActiveFilters(true);
  };
  const handleStatusSelect = (status: string) => {
    setPaginationModel((prev) => ({
      ...prev,
      filters: [
        ...prev.filters.filter((f) => f.id !== 'status'),
        { id: 'status', value: status }
      ]
    }));
    setAnchorElStatus(null);
    setSelectedStatus(status);
    setHasActiveFilters(true);
  };
  const scanNameValues = [
    'censys',
    'amass',
    'asm_sync',
    'credential_sync',
    'cybersixgill',
    'findomain',
    'intel_x_identity',
    'portscanner',
    'wappalyzer',
    'censysIpv4',
    'censysCertificates',
    'refresh_vs_summaries',
    'sslyze',
    'searchSync',
    'shodan_sync',
    'sync_asm_sync',
    'cve',
    'cisakev',
    'nist',
    'dotgov',
    'intrigueIdent',
    'shodan',
    'lookingGlass',
    'dnstwist',
    'databricks',
    'rootDomainSync',
    'was_sync',
    'was',
    'xpanse_sync'
  ];

  const statusValues = [
    'created',
    'queued',
    'requested',
    'started',
    'finished',
    'failed'
  ];

  const isLocal = import.meta.env.VITE_IS_LOCAL === '1';

  const filteredScanNameValues = isLocal
    ? scanNameValues.filter((name) => name !== 'databricks')
    : scanNameValues;

  const scanNameDropdown = (
    <>
      <MuiButton
        size="small"
        sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
        endIcon={<KeyboardArrowDown />}
        onClick={handleNameClick}
      >
        Name: {selectedName! || ('Select' as any)}
      </MuiButton>
      <Menu
        anchorEl={anchorElName}
        open={openNameMenu}
        onClose={() => setAnchorElName(null)}
      >
        {filteredScanNameValues.map((name, index) => (
          <MenuItem
            key={index + name}
            value={name}
            onClick={handleNameSelect.bind(null, name)}
          >
            {name}
          </MenuItem>
        ))}
      </Menu>
    </>
  );

  const scanStatusDropdown = (
    <>
      <MuiButton
        size="small"
        sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
        endIcon={<KeyboardArrowDown />}
        onClick={handleStatusClick}
      >
        Status: {selectedStatus! || ('Select' as any)}
      </MuiButton>
      <Menu
        anchorEl={anchorElStatus}
        open={openStatusMenu}
        onClose={() => setAnchorElStatus(null)}
      >
        {statusValues.map((status, index) => (
          <MenuItem
            key={index + status}
            value={status}
            onClick={handleStatusSelect.bind(null, status)}
          >
            {status}
          </MenuItem>
        ))}
      </Menu>
    </>
  );

  const resetScans = useCallback(() => {
    if (filterTimerRef.current) {
      clearTimeout(filterTimerRef.current);
      filterTimerRef.current = null;
    }
    setFilterModel({ items: [] });
    setHasActiveFilters(false);
    setSelectedName('');
    setSelectedStatus('');
    setPaginationModel((prev) => ({
      ...prev,
      page: 0,
      pageSize: DEFAULT_DATA_GRID_PAGE_SIZE,
      filters: []
    }));
  }, []);

  return (
    <Box width="100%">
      {errors.global && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errors.global}
        </Alert>
      )}
      {isLoading && (
        <Paper elevation={2} sx={{ mb: 2 }}>
          <Alert severity="info">Loading Scan History...</Alert>
        </Paper>
      )}
      <Paper elevation={2} sx={{ width: '100%' }}>
        <CustomDataGrid
          rows={scansTasksRows}
          rowCount={totalResults}
          columns={scansTasksCols}
          loading={isLoading}
          slots={{ toolbar: CustomToolbar, pagination: CustomPagination }}
          slotProps={{
            toolbar: {
              children: [scanNameDropdown, scanStatusDropdown].map(
                (child, index) => <Box key={index}>{child}</Box>
              ),
              exportTitle: 'Scans',
              hasActiveFilters
            } as any,
            basePopper: {
              placement: 'bottom-start'
            }
          }}
          paginationMode="server"
          paginationModel={paginationModel}
          onPaginationModelChange={(model) => {
            fetchScanTasks({
              page: model.page + 1,
              pageSize: model.pageSize,
              sort: paginationModel.sort,
              filters: paginationModel.filters
            });
          }}
          filterMode="server"
          filterModel={filterModel}
          onFilterModelChange={(model) => {
            const cleanedModel = cleanFilterModelItems(model, filterModel);
            const emptyModel = isFilterModelEmpty(cleanedModel);
            const dropdownFilters = paginationModel.filters.filter(
              (filter) => filter.id === 'name' || filter.id === 'status'
            );
            const nextFilters = [
              ...dropdownFilters,
              ...cleanedModel.items.map((item) => ({
                id: item.field,
                value: item.value
              }))
            ];

            setFilterModel(cleanedModel);
            setHasActiveFilters(!emptyModel || dropdownFilters.length > 0);

            if (filterTimerRef.current) {
              clearTimeout(filterTimerRef.current);
              filterTimerRef.current = null;
            }

            filterTimerRef.current = window.setTimeout(() => {
              setPaginationModel((prev) => ({
                ...prev,
                page: 0,
                filters: nextFilters
              }));
              filterTimerRef.current = null;
            }, SERVER_FILTER_DEBOUNCE_MS);
          }}
          pageSizeOptions={DATA_GRID_PAGE_SIZE_OPTIONS}
          disableRowSelectionOnClick
          showToolbar
        />
      </Paper>
      {scanTasks?.length === 0 && !isLoading && (
        <MuiButton
          aria-label="Reset scan table"
          onClick={resetScans}
          variant="contained"
          color="primary"
          sx={{ width: 'fit-content', mt: 2 }}
        >
          Refresh Scan History
        </MuiButton>
      )}
      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
        scroll="paper"
        fullWidth
        maxWidth="xl"
      >
        <DialogTitle id="alert-dialog-title">Scan Details</DialogTitle>
        <DialogContent>
          {detailsParams?.row?.fargate_task_arn && (
            <Box pb={2}>
              <Typography variant="h6" component="div">
                Logs:
              </Typography>

              {detailsParams?.row?.fargate_task_arn.match && (
                <MuiButton
                  aria-label="View all on CloudWatch"
                  variant="text"
                  target="_blank"
                  rel="noopener noreferrer"
                  href={`${
                    import.meta.env.VITE_CLOUDWATCH_URL
                  }#logsV2:log-groups/log-group/${import.meta.env.VITE_FARGATE_LOG_GROUP!}/log-events/worker$252Fmain$252F${
                    (detailsParams?.row?.fargate_task_arn.match('.*/(.*)') || [
                      ''
                    ])[1]
                  }`}
                >
                  {' '}
                  View all on CloudWatch
                </MuiButton>
              )}
              <Log
                token={token ?? ''}
                url={`${import.meta.env.VITE_API_URL}/scan-tasks/${detailsParams?.row?.id}/logs`}
              />
            </Box>
          )}
          {(() => {
            const rawInput = detailsParams?.row?.input;
            if (!rawInput || rawInput === 'null') {
              return (
                <>
                  <Typography variant="h6" component="div">
                    Input:
                  </Typography>
                  <Typography variant="logText">
                    No input data available.
                  </Typography>
                </>
              );
            }
            try {
              const parsedJSON = JSON.parse(rawInput);
              const formattedJSON = JSON.stringify(parsedJSON, null, 2);
              return (
                <>
                  <Typography variant="h3">Input:</Typography>
                  <pre>{formattedJSON}</pre>
                </>
              );
            } catch (e) {
              logger.error('ScanTasksView.renderInput JSON parse failed:', {
                error: e
              });
              return (
                <>
                  <Typography variant="h6" component="div" pt={2}>
                    Input:
                  </Typography>
                  <Typography color="error" variant="h3">
                    Invalid input data format.
                  </Typography>
                </>
              );
            }
          })()}
          <Typography variant="h6" component="div" pt={2}>
            Output:
          </Typography>
          <Typography variant="logText">
            {detailsParams?.row?.output || 'None'}
          </Typography>

          {detailsParams?.row.status !== 'finished' &&
            detailsParams?.row.status !== 'failed' && (
              <>
                <Typography variant="h6" component="div">
                  Actions:
                </Typography>
                <MuiButton
                  aria-label="Kill scan task"
                  variant="contained"
                  href="# "
                  onClick={(e) => {
                    e.preventDefault();
                    killScanTask2(detailsParams?.row.id);
                  }}
                >
                  Kill Scan
                </MuiButton>
              </>
            )}
        </DialogContent>
        <DialogContent>
          <Stack spacing={2} direction="row" justifyContent="end">
            <MuiButton
              variant="contained"
              aria-label="Close scan details"
              onClick={() => setOpenDialog(false)}
            >
              Close
            </MuiButton>
          </Stack>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default ScanTasksView;
