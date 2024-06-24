import React, { useCallback, useEffect, useState } from 'react';
import { TableInstance, Column, CellProps, Row } from 'react-table';
import { Query, Scan } from 'types';
import { Table, Paginator, ColumnFilter, selectFilter } from 'components';
import { ScanTask } from 'types';
import { useAuthContext } from 'context';
// @ts-ignore:next-line
import { formatDistanceToNow, parseISO, set } from 'date-fns';
import classes from './Scans.module.scss';
import { FaMinus, FaPlus, FaSyncAlt } from 'react-icons/fa';
import { LazyLog } from 'react-lazylog';
import { Button } from '@trussworks/react-uswds';
import {
  Alert,
  Button as MuiButton,
  Dialog,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Icon,
  IconButton,
  Menu,
  MenuItem,
  Paper,
  Typography
} from '@mui/material';
import { Box } from '@mui/system';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import { KeyboardArrowDown } from '@mui/icons-material';
// import { da } from 'date-fns/locale';

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

  // const killScanTask = async (id: string) => {
  //   try {
  //     await apiPost(`/scan-tasks/${id}/kill`, { body: {} });
  //     const index = scanTasks.findIndex((task) => task.id === id);
  //     setScanTasks(
  //       Object.assign([], scanTasks, {
  //         [index]: {
  //           ...scanTasks[index],
  //           status: 'failed'
  //         }
  //       })
  //     );
  const killScanTask = async (index: number) => {
    try {
      const row = scanTasks[index];
      await apiPost(`/scan-tasks/${row.id}/kill`, { body: {} });
      setScanTasks(
        Object.assign([], scanTasks, {
          [index]: {
            ...row,
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

  const renderExpanded = (row: Row<ScanTask>) => {
    const { original } = row;
    return (
      <div className={classes.expandedRoot}>
        {original.fargateTaskArn && (
          <>
            <h4>
              Logs
              {original.fargateTaskArn?.match('.*/(.*)') && (
                <a
                  target="_blank"
                  rel="noopener noreferrer"
                  href={`https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/${process
                    .env
                    .REACT_APP_FARGATE_LOG_GROUP!}/log-events/worker$252Fmain$252F${
                    (original.fargateTaskArn.match('.*/(.*)') || [])[1]
                  }`}
                >
                  {' '}
                  (View all on CloudWatch)
                </a>
              )}
            </h4>

            <Log
              token={token ?? ''}
              url={`${process.env.REACT_APP_API_URL}/scan-tasks/${original.id}/logs`}
            />
          </>
        )}

        <h4>Input</h4>
        <small>
          <pre>{JSON.stringify(JSON.parse(original.input), null, 2)}</pre>
        </small>
        <h4>Output</h4>
        <small>
          <pre>{original.output || 'None'}</pre>
        </small>

        {row.original.status !== 'finished' &&
          row.original.status !== 'failed' && (
            <>
              <h4>Actions</h4>
              <a
                href="# "
                onClick={(e) => {
                  e.preventDefault();
                  killScanTask(row.index);
                }}
              >
                Kill
              </a>
            </>
          )}
      </div>
    );
  };

  const columns: Column<ScanTask>[] = [
    {
      Header: 'ID',
      accessor: 'id',
      Filter: ColumnFilter,
      disableSortBy: true,
      disableFilters: true
    },
    {
      Header: 'Status',
      accessor: 'status',
      Filter: selectFilter([
        'created',
        'queued',
        'requested',
        'started',
        'finished',
        'failed'
      ]),
      disableSortBy: true
    },
    {
      Header: 'Name',
      id: 'name',
      accessor: ({ scan }) => scan?.name,
      Filter: selectFilter([
        // TODO: sync this with the SCAN_SCHEMA
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
      ]),
      disableSortBy: true
    },
    {
      Header: 'Created At',
      id: 'createdAt',
      accessor: ({ createdAt }) => dateAccessor(createdAt),
      disableFilters: true
    },
    {
      Header: 'Finished At',
      id: 'finishedAt',
      accessor: ({ finishedAt }) => dateAccessor(finishedAt),
      disableFilters: true
    },
    {
      Header: 'Details',
      Cell: ({ row }: CellProps<ScanTask>) => (
        <span
          {...row.getToggleRowExpandedProps()}
          className="text-center display-block"
        >
          {row.isExpanded ? <FaMinus /> : <FaPlus />}
        </span>
      ),
      disableFilters: true
    }
  ];
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
              order: sort[0]?.desc ? 'DESC' : 'ASC',
              filters: tableFilters
            }
          }
        );
        if (result.length === 0) return;
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

  const renderPagination = (table: TableInstance<ScanTask>) => (
    <Paginator table={table} totalResults={totalResults} />
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

  return (
    <>
      {errors.global && <p className={classes.error}>{errors.global}</p>}
      <Table<ScanTask>
        renderPagination={renderPagination}
        columns={columns}
        data={scanTasks}
        pageCount={Math.ceil(totalResults / PAGE_SIZE)}
        fetchData={fetchScanTasks}
        pageSize={PAGE_SIZE}
        initialSortBy={[
          {
            id: 'createdAt',
            desc: true
          }
        ]}
        renderExpanded={renderExpanded}
      />
      <Box mb={3}>
        <Paper elevation={0}>
          {scanTasks?.length === 0 ? (
            <Alert severity="warning">No scans found</Alert>
          ) : (
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
          )}
        </Paper>
      </Box>
      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">{'Scan Details'}</DialogTitle>
        <DialogContent>
          <Typography variant="h6" component="div">
            Logs
          </Typography>
          <Typography variant="body2" color="text.secondary" component="div">
            {detailsParams?.row?.fargateTaskArn && (
              <>
                <Log
                  token={token ?? ''}
                  url={`${process.env.REACT_APP_API_URL}/scan-tasks/${detailsParams?.row?.id}/logs`}
                />
                <a
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
                  (View all on CloudWatch)
                </a>
              </>
            )}
          </Typography>
          <Typography variant="h6" component="div">
            Input
          </Typography>
          <Typography variant="body2" color="text.secondary" component="div">
            <pre>
              {detailsParams?.row?.input &&
                JSON.stringify(JSON.parse(detailsParams?.row?.input), null, 2)}
            </pre>
          </Typography>
          <Typography variant="h6" component="div">
            Output
          </Typography>
          <Typography variant="body2" color="text.secondary" component="div">
            <pre>
              {detailsParams?.row?.output &&
                JSON.stringify(JSON.parse(detailsParams?.row?.output), null, 2)}
            </pre>
          </Typography>

          {detailsParams?.row.status !== 'finished' &&
            detailsParams?.row.status !== 'failed' && (
              <>
                <h4>Actions</h4>
                <a
                  href="# "
                  onClick={(e) => {
                    e.preventDefault();
                    killScanTask(detailsParams?.row.id);
                  }}
                >
                  Kill
                </a>
              </>
            )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ScanTasksView;
