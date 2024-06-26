import React, { useCallback, useEffect, useState } from 'react';
import { Query, Scan } from 'types';
import { ScanTask } from 'types';
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
  createdAt: string;
  startedAt: string;
  requestedAt: string;
  finishedAt: string;
  scan: Scan;
  fargateTaskArn: string;
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
          e.status === 422 ? 'Unable to kill scan' : e.message ?? e.toString()
      });
      console.log(e);
    }
  };

  const PAGE_SIZE = 15;

  const fetchScanTasks = useCallback(
    async (query: Query<ScanTask>) => {
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
          if ('rootDomains' in currentOrganization)
            tableFilters['organization'] = currentOrganization.id;
          else tableFilters['tag'] = currentOrganization.id;
        }
        const { result, count } = await apiPost<ApiResponse>(
          '/scan-tasks/search',
          {
            body: {
              page,
              pageSize: query.pageSize ?? PAGE_SIZE,
              sort: sort[0]?.id ?? 'createdAt',
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
    name: scanTask.scan?.name ?? 'None',
    input: scanTask.input,
    output: scanTask.output,
    createdAt: dateAccessor(scanTask.createdAt),
    startedAt: dateAccessor(scanTask.startedAt),
    requestedAt: scanTask.requestedAt,
    finishedAt: dateAccessor(scanTask.finishedAt),
    scan: scanTask.scan,
    fargateTaskArn: scanTask.fargateTaskArn
  }));

  const scansTasksCols: GridColDef[] = [
    { field: 'id', headerName: 'ID', minWidth: 100, flex: 2 },
    { field: 'status', headerName: 'Status', minWidth: 100, flex: 1 },
    { field: 'name', headerName: 'Name', minWidth: 100, flex: 1 },
    { field: 'createdAt', headerName: 'Created At', minWidth: 200, flex: 1 },
    { field: 'finishedAt', headerName: 'Finished At', minWidth: 200, flex: 1 },
    {
      field: 'details',
      headerName: 'Details',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            aria-label={`Details for scan task ${cellValues.row.id}`}
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
    'findomain',
    'portscanner',
    'wappalyzer',
    'censysIpv4',
    'censysCertificates',
    'sslyze',
    'searchSync',
    'cve',
    'dotgov',
    'webscraper',
    'intrigueIdent',
    'shodan',
    'hibp',
    'lookingGlass',
    'dnstwist',
    'rootDomainSync'
  ];

  const statusValues = [
    'created',
    'queued',
    'requested',
    'started',
    'finished',
    'failed'
  ];

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
        {scanNameValues.map((name, index) => (
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
                  )
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
          {detailsParams?.row?.fargateTaskArn && (
            <>
              <Typography variant="h6" component="div">
                Logs:
              </Typography>

              {detailsParams?.row?.fargateTaskArn.match && (
                <MuiButton
                  aria-label="View all on CloudWatch"
                  variant="text"
                  target="_blank"
                  rel="noopener noreferrer"
                  href={`https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/${process
                    .env
                    .REACT_APP_FARGATE_LOG_GROUP!}/log-events/worker$252Fmain$252F${
                    (detailsParams?.row?.fargateTaskArn.match('.*/(.*)') || [
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
                url={`${process.env.REACT_APP_API_URL}/scan-tasks/${detailsParams?.row?.id}/logs`}
              />
            </>
          )}
          <Typography variant="h6" component="div">
            Input:
          </Typography>
          <pre>
            {detailsParams?.row?.input &&
              JSON.stringify(JSON.parse(detailsParams?.row?.input), null, 2)}
          </pre>

          <Typography variant="h6" component="div">
            Output:
          </Typography>
          <pre>{detailsParams?.row?.output || 'None'}</pre>

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
