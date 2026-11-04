// React
import React, { useCallback, useRef, useState } from 'react';

// Icons
import Delete from '@mui/icons-material/Delete';
import PlayCircleFilledIcon from '@mui/icons-material/PlayCircleFilled';
import Add from '@mui/icons-material/Add';

// Date utilities
import { formatDistanceToNow, parseISO } from 'date-fns';

// Styles & Utils
import classes from './Scans.module.scss';
import { textFilterOperators } from '@/utils/transformTableData';
import { logger } from '@/utils/logger';

// Material-UI Components
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Snackbar from '@mui/material/Snackbar';
import Typography from '@mui/material/Typography';
import { GridColDef, GridRenderCellParams } from '@mui/x-data-grid';

// Local Components & Context
import CustomDataGrid from '@/components/DataGrid/CustomDataGrid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import { Scan, Organization, ScanSchema, OrganizationTag } from 'types';
import { useAuthContext } from 'context';
import { ScanForm, ScanFormValues } from 'components/ScanForm';
import { ENDPOINTS } from '@/constants/endpoints';
import ConfirmDialog from '@/components/Dialog/ConfirmDialog';

interface Errors extends Partial<Scan> {
  global?: string;
  scheduler?: string;
}

export interface OrganizationOption {
  label: string;
  value: string;
}

export interface ScansRow {
  id: string;
  name: string;
  tags: string;
  mode: string;
  frequency: number;
  last_run: string;
  description: string;
  concurrent_tasks: number;
}

const ScansView: React.FC = () => {
  const { apiGet, apiPost, apiDelete } = useAuthContext();
  const [selectedId, setSelectedId] = useState<string>('');
  const [selectedName, setSelectedName] = useState<string>('');
  const [scans, setScans] = useState<Scan[]>([]);
  const [organizationOptions, setOrganizationOptions] = useState<
    OrganizationOption[]
  >([]);
  const [tags, setTags] = useState<OrganizationTag[]>([]);
  const [scanSchema, setScanSchema] = useState<ScanSchema>({});
  const [deleteScanDialogOpen, setDeleteScanDialogOpen] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [runScanDialogOpen, setRunScanDialogOpen] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');
  const [newScanDialogOpen, setNewScanDialogOpen] = useState(false);

  const [values] = useState<ScanFormValues>({
    name: 'censys',
    arguments: '{}',
    organizations: [],
    frequency: 1,
    frequencyUnit: 'minute',
    is_granular: false,
    is_user_modifiable: false,
    is_single_scan: false,
    tags: [],
    concurrent_tasks: 1,
    useDateRange: false
  });

  const fetchScans = useCallback(async () => {
    try {
      const { scans, organizations, schema } = await apiGet<{
        scans: Scan[];
        organizations: Organization[];
        schema: ScanSchema;
      }>(ENDPOINTS.SCANS);
      const tags = await apiGet<OrganizationTag[]>(
        ENDPOINTS.ORGANIZATIONS_TAGS
      );
      setScans(scans);
      setScanSchema(schema);
      setOrganizationOptions(
        organizations.map((e) => ({ label: e.name, value: e.id }))
      );
      setTags(tags);
    } catch (e) {
      logger.error('ScansView.fetchScans failed:', { error: e });
    }
  }, [apiGet]);

  const deleteRow = async (id: string) => {
    try {
      await apiDelete(ENDPOINTS.SCAN.replace('{scan_id}', id));
      setScans(scans.filter((scan) => scan.id !== id));
    } catch (e: any) {
      setErrors({
        global:
          e.status === 422
            ? 'Unable to delete scan'
            : (e.message ?? e.toString())
      });
      logger.error('ScansView.deleteRow failed:', { error: e, scanId: id });
    }
  };

  const setFrequency = async (body: ScanFormValues) => {
    if (body.is_single_scan) body.frequency = 1;
    if (body.frequencyUnit === 'minute') body.frequency *= 60;
    else if (body.frequencyUnit === 'hour') body.frequency *= 60 * 60;
    else body.frequency *= 60 * 60 * 24;
  };

  const onSubmit = async (body: ScanFormValues) => {
    try {
      // For now, parse the arguments as JSON. We'll want to add a GUI for this in the future
      body.arguments = JSON.parse(body.arguments);
      setFrequency(body);

      const scan = await apiPost<Scan>(ENDPOINTS.SCANS, {
        body: {
          ...body,
          organizations: body.organizations
            ? body.organizations.map((e) => e.value)
            : [],
          tags: body.tags ? body.tags.map((e) => ({ id: e.value })) : []
        }
      });

      setScans(scans.concat(scan));
      setSnackbarMsg('Scan created successfully!');
      setSnackbarOpen(true);
      setNewScanDialogOpen(false);
    } catch (e: any) {
      setErrors({
        global: e.message ?? e.toString()
      });
      setSnackbarMsg(`Scan creation failed: ${e.message ?? e.toString()}`);
      setSnackbarOpen(true);
      logger.error('ScansView.createScan failed:', { error: e });
    }
  };

  const invokeScheduler = async () => {
    setErrors({ ...errors, scheduler: '' });
    try {
      await apiPost(ENDPOINTS.SCAN_SCHEDULER, { body: {} });
    } catch (e) {
      logger.error('ScansView.invokeScheduler failed:', { error: e });
      setErrors({ ...errors, scheduler: 'Invocation failed.' });
    }
  };

  const formatFrequency = (frequency: number): string => {
    if (frequency >= 86400 && frequency % 86400 === 0) {
      const days = frequency / 86400;
      return `${days} day${days > 1 ? 's' : ''}`;
    } else if (frequency >= 3600 && frequency % 3600 === 0) {
      const hours = frequency / 3600;
      return `${hours} hour${hours > 1 ? 's' : ''}`;
    } else if (frequency >= 60 && frequency % 60 === 0) {
      const minutes = frequency / 60;
      return `${minutes} minute${minutes > 1 ? 's' : ''}`;
    } else {
      return `${frequency} second${frequency !== 1 ? 's' : ''}`;
    }
  };

  /**
   * Manually runs a single scan, then immediately invokes the
   * scheduler so the scan is run.
   * @param id Scan ID
   */

  const runScan = async (id: string) => {
    try {
      await apiPost(ENDPOINTS.SCAN_RUN.replace('{scan_id}', id), { body: {} });
    } catch (e) {
      logger.error('ScansView.runScan failed:', { error: e, scanId: id });
      setErrors({ ...errors, scheduler: 'Run failed.' });
    }
    await invokeScheduler();
  };

  type SnackbarCloseReason = 'timeout' | 'clickaway';
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  const handleSnackbarClose = (
    event: React.SyntheticEvent<any> | Event,
    reason?: SnackbarCloseReason
  ) => {
    if (reason === 'clickaway') return;
    setSnackbarOpen(false);
    triggerRef.current?.focus();
  };

  React.useEffect(() => {
    fetchScans();
  }, [fetchScans]);

  const scansRows: ScansRow[] = scans.map((scan) => {
    return {
      id: scan.id,
      name: scan.name,
      tags: scan.tags.map((tag) => tag.name).join(', '),
      mode:
        scanSchema[scan.name] && scanSchema[scan.name].is_passive
          ? 'Passive'
          : 'Active',
      frequency: scan.frequency,
      last_run:
        !scan.last_run ||
        new Date(scan.last_run).getTime() === new Date(0).getTime()
          ? 'None'
          : `${formatDistanceToNow(parseISO(scan.last_run))} ago`,
      description: scanSchema[scan.name]?.description,
      concurrent_tasks: scan.concurrent_tasks,
      is_single_scan: scan.is_single_scan
    };
  });

  const scansCols: GridColDef[] = [
    {
      field: 'run',
      headerName: 'Run',
      minWidth: 50,
      flex: 0.5,
      disableExport: true,
      filterable: false,
      sortable: false,
      disableColumnMenu: true,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            aria-label={`Run ${cellValues.row.name} scan.`}
            tabIndex={cellValues.tabIndex}
            color="primary"
            onClick={() => {
              setSelectedId(cellValues.row.id);
              setSelectedName(cellValues.row.name);
              setRunScanDialogOpen(true);
            }}
          >
            <PlayCircleFilledIcon />
          </IconButton>
        );
      }
    },
    {
      field: 'name',
      headerName: 'Name',
      minWidth: 130,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Scan name: ${cellValues.row.name}`}
          >
            {cellValues.row.name}
          </Box>
        );
      }
    },
    {
      field: 'tags',
      headerName: 'Tags',
      minWidth: 65,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Tags for ${cellValues.row.name} scan: ${cellValues.row.tags}`}
          >
            {cellValues.row.tags}
          </Box>
        );
      }
    },
    {
      field: 'mode',
      headerName: 'Mode',
      minWidth: 80,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Mode for ${cellValues.row.name} scan: ${cellValues.row.mode}`}
          >
            {cellValues.row.mode}
          </Box>
        );
      }
    },
    {
      field: 'frequency',
      headerName: 'Frequency',
      minWidth: 100,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (params: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={
              params.row.is_single_scan
                ? `Frequency for ${params.row.name} scan: Single Scan`
                : `Frequency for ${params.row.name} scan: ${formatFrequency(Number(params.value))}`
            }
          >
            {params.row.is_single_scan
              ? 'Single Scan'
              : formatFrequency(Number(params.value))}
          </Box>
        );
      }
    },
    {
      field: 'last_run',
      headerName: 'Last Run',
      minWidth: 100,
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Last run for ${cellValues.row.name} scan: ${cellValues.row.last_run}`}
          >
            {cellValues.row.last_run}
          </Box>
        );
      }
    },
    {
      field: 'concurrent_tasks',
      headerName: 'Concurrent Tasks',
      minWidth: 100,
      flex: 1,
      filterOperators: textFilterOperators,
      align: 'center',
      headerAlign: 'center',
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Concurrent tasks for ${cellValues.row.name} scan: ${cellValues.row.concurrent_tasks}`}
          >
            {cellValues.row.concurrent_tasks}
          </Box>
        );
      }
    },
    {
      field: 'delete',
      headerName: 'Delete',
      minWidth: 50,
      flex: 1,
      disableExport: true,
      filterable: false,
      sortable: false,
      disableColumnMenu: true,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            aria-label={`Delete ${cellValues.row.name} scan.`}
            tabIndex={cellValues.tabIndex}
            color="primary"
            onClick={() => {
              setDeleteScanDialogOpen(true);
              setSelectedId(cellValues.row.id);
              setSelectedName(cellValues.row.name);
            }}
          >
            <Delete />
          </IconButton>
        );
      }
    },
    {
      field: 'description',
      headerName: 'Description',
      minWidth: 250,
      flex: 5,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Description for ${cellValues.row.name} scan: ${cellValues.row.description}`}
          >
            {cellValues.row.description}
          </Box>
        );
      }
    }
  ];

  //To-do: Add a button to toolbar to import scans
  //To-do: Dialogs/Modals need to be built for Import. Export is already handled by MUI DataGrid.

  const confirmDeleteScanDialog = (
    <ConfirmDialog
      isOpen={deleteScanDialogOpen}
      onConfirm={() => {
        deleteRow(selectedId);
        setDeleteScanDialogOpen(false);
      }}
      onCancel={() => setDeleteScanDialogOpen(false)}
      title={'Delete scan?'}
      content={
        <>
          <Typography mb={3}>
            Are you sure you would like to delete the{' '}
            <code>{selectedName}</code> scan?
          </Typography>
        </>
      }
      screenWidth="xs"
    />
  );
  const confirmRunScanDialog = (
    <ConfirmDialog
      isOpen={runScanDialogOpen}
      onConfirm={() => {
        runScan(selectedId);
        setRunScanDialogOpen(false);
      }}
      onCancel={() => setRunScanDialogOpen(false)}
      title={'Run scan?'}
      content={
        <>
          <Typography mb={3}>
            Are you sure you would like to run the <code>{selectedName}</code>{' '}
            scan?
          </Typography>
        </>
      }
      screenWidth="xs"
    />
  );
  const addNewScanDialog = (
    <ConfirmDialog
      isOpen={newScanDialogOpen}
      onCancel={() => setNewScanDialogOpen(false)}
      title={'Add a Scan'}
      content={
        <ScanForm
          organizationOption={organizationOptions}
          tags={tags}
          propValues={values}
          onSubmit={onSubmit}
          type="create"
          scanSchema={scanSchema}
        />
      }
      screenWidth="xs"
    />
  );
  const addNewScan = (
    <Button
      size="small"
      sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
      startIcon={<Add />}
      onClick={() => {
        setNewScanDialogOpen(true);
      }}
    >
      Add New Scan
    </Button>
  );
  return (
    <>
      <Box mb={3}>
        {confirmRunScanDialog}
        <Paper elevation={0}>
          {scans?.length === 0 ? (
            <Alert severity="info">No scans found</Alert>
          ) : (
            <CustomDataGrid
              rows={scansRows}
              columns={scansCols}
              showToolbar
              slots={{ toolbar: CustomToolbar }}
              slotProps={{
                basePopper: { placement: 'bottom-start' },
                toolbar: {
                  children: addNewScan,
                  exportTitle: 'Scans'
                } as any,
                columnsManagement: {
                  disableResetButton: true,
                  getTogglableColumns: (columns) => {
                    const alwaysVisible = ['name'];
                    return columns
                      .filter(
                        (col) => col.field && !alwaysVisible.includes(col.field)
                      )
                      .map((col) => col.field as string);
                  }
                }
              }}
            />
          )}
        </Paper>
      </Box>
      <Button variant="contained" color="primary" onClick={invokeScheduler}>
        Manually run scheduler
      </Button>
      {errors.scheduler && <p className={classes.error}>{errors.scheduler}</p>}
      {errors.global && <p className={classes.error}>{errors.global}</p>}
      {addNewScanDialog}
      {confirmDeleteScanDialog}
      <Snackbar
        open={snackbarOpen}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbarMsg.includes('failed') ? 'error' : 'success'}
          sx={{ width: '100%' }}
        >
          <span>{snackbarMsg}</span>
        </Alert>
      </Snackbar>
    </>
  );
};

export default ScansView;
