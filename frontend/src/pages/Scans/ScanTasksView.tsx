import React, { useCallback, useEffect, useState } from 'react';
import { OrgQuery } from 'types';
import { Scan, ScanTask } from 'types';
import { useAuthContext } from 'context';
// @ts-ignore:next-line
import { formatDistanceToNow, parseISO } from 'date-fns';
import classes from './Scans.module.scss';
import { FaSyncAlt } from 'react-icons/fa';
import { LazyLog } from 'react-lazylog';
import { Button } from '@trussworks/react-uswds';
import {
  Alert,
  Button as MuiButton,
  Dialog,
  DialogContent,
  DialogTitle,
  Icon,
  IconButton,
  Menu,
  MenuItem,
  Paper,
  Typography
} from '@mui/material';
import { Box, Stack } from '@mui/system';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import { KeyboardArrowDown } from '@mui/icons-material';

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
    <div className={classes.logContainer}>
      <LazyLog
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
      <Button
        aria-label="Refresh log "
        type="button"
        outline
        size={'small' as any}
        onClick={() => setLogKey(Math.random())}
      >
        <FaSyncAlt />
      </Button>
    </div>
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
      await apiPost(`/scan-tasks/${id}/kill`, { body: {} });
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
      console.error(e);
    }
  };

  const PAGE_SIZE = 15;

  const fetchScanTasks = useCallback(
    async (query: OrgQuery<ScanTask>) => {
      const { page, sort, filters } = query;
      try {
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
          '/scan-tasks/search',
          {
            body: {
              page,
              pageSize: query.pageSize ?? PAGE_SIZE,
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
          pageSize: query.pageSize ?? PAGE_SIZE,
          pageCount: Math.ceil(count / (query.pageSize ?? PAGE_SIZE))
        }));
      } catch (e) {
        console.error(e);
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
      headerName: 'ID',
      minWidth: 100,
      flex: 2,
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
      minWidth: 100,
      flex: 1,
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
      minWidth: 200,
      flex: 1,
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
      minWidth: 200,
      flex: 1,
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
      minWidth: 100,
      flex: 1,
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
            <Icon>info</Icon>
          </IconButton>
        );
      }
    }
  ];

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: PAGE_SIZE,
    sort: [],
    filters: [] as { id: string; value: any }[]
  });

  useEffect(() => {
    fetchScanTasks({
      page: 1,
      pageSize: PAGE_SIZE,
      sort: paginationModel.sort,
      filters: paginationModel.filters
    });
  }, [fetchScanTasks, paginationModel.sort, paginationModel.filters]);

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
    'redshift',
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
    ? scanNameValues.filter((name) => name !== 'redshift')
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
    fetchScanTasks({
      page: 1,
      pageSize: PAGE_SIZE,
      sort: [],
      filters: []
    });
  }, [fetchScanTasks]);

  return (
    <>
      {errors.global && <p className={classes.error}>{errors.global}</p>}
      <Box mb={3} display="flex" justifyContent="center">
        {scanTasks?.length === 0 ? (
          <Stack direction="row" spacing={2}>
            <Paper elevation={2}>
              <Alert severity="warning">No results found.</Alert>
            </Paper>
            <MuiButton
              aria-label="Reset scan table"
              onClick={resetScans}
              variant="contained"
              color="primary"
              sx={{ width: 'fit-content' }}
            >
              Reset
            </MuiButton>
          </Stack>
        ) : (
          <Paper elevation={2} sx={{ width: '100%' }}>
            <DataGrid
              rows={scansTasksRows}
              rowCount={totalResults}
              columns={scansTasksCols}
              slots={{ toolbar: CustomToolbar }}
              slotProps={{
                toolbar: {
                  children: [scanNameDropdown, scanStatusDropdown].map(
                    (child, index) => <Box key={index}>{child}</Box>
                  ),
                  exportTitle: 'Scans'
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
              onFilterModelChange={(model) => {
                fetchScanTasks({
                  page: 1,
                  pageSize: paginationModel.pageSize,
                  sort: paginationModel.sort,
                  filters: model.items.map((item) => ({
                    id: item.field,
                    value: item.value
                  }))
                });
              }}
              pageSizeOptions={[15, 30, 50, 100]}
              disableRowSelectionOnClick
              showToolbar
            />
          </Paper>
        )}
      </Box>
      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
        scroll="paper"
        fullWidth
        maxWidth="lg"
      >
        <DialogTitle id="alert-dialog-title">{'Scan Details'}</DialogTitle>
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
              console.error(e);
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
    </>
  );
};

export default ScanTasksView;
