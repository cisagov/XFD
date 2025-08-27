import classes from './Scans.module.scss';
import React, { useCallback, useRef, useState } from 'react';
// TODO: Refactor to use Material-UI components
import {
  Button,
  Modal,
  ButtonGroup,
  ModalFooter,
  ModalHeading,
  ModalRef
} from '@trussworks/react-uswds';
import { ModalToggleButton } from 'components';
// import { Column, CellProps } from 'react-table';
import { Scan, Organization, ScanSchema, OrganizationTag } from 'types';
// import { FaTimes, FaEdit } from 'react-icons/fa';
import { FaTimes } from 'react-icons/fa';
import { FaPlayCircle } from 'react-icons/fa';
import { useAuthContext } from 'context';
// @ts-ignore:next-line
import { formatDistanceToNow, parseISO } from 'date-fns';
// import { Link } from 'react-router-dom';
import { setFrequency } from 'pages/Scan/Scan';
import { ScanForm, ScanFormValues } from 'components/ScanForm';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';

import {
  Alert,
  Button as MuiButton,
  Box,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  IconButton,
  Paper,
  DialogTitle,
  Snackbar,
  SnackbarCloseReason
} from '@mui/material';
//Needed for the CustomToolbar:
// import CustomToolbar from 'components/DataGrid/CustomToolbar';
// import { Add, Publish } from '@mui/icons-material';

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
  const deleteModalRef = useRef<ModalRef>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [open, setOpen] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');

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
    concurrent_tasks: 1
  });

  const fetchScans = useCallback(async () => {
    try {
      const { scans, organizations, schema } = await apiGet<{
        scans: Scan[];
        organizations: Organization[];
        schema: ScanSchema;
      }>('/scans');
      const tags = await apiGet<OrganizationTag[]>(`/organizations/tags`);
      setScans(scans);
      setScanSchema(schema);
      setOrganizationOptions(
        organizations.map((e) => ({ label: e.name, value: e.id }))
      );
      setTags(tags);
    } catch (e) {
      console.error(e);
    }
  }, [apiGet]);

  const deleteRow = async (id: string) => {
    try {
      await apiDelete(`/scans/${id}`, { body: {} });
      setScans(scans.filter((scan) => scan.id !== id));
    } catch (e: any) {
      setErrors({
        global:
          e.status === 422
            ? 'Unable to delete scan'
            : (e.message ?? e.toString())
      });
      console.log(e);
    }
  };

  const onSubmit = async (body: ScanFormValues) => {
    try {
      // For now, parse the arguments as JSON. We'll want to add a GUI for this in the future
      body.arguments = JSON.parse(body.arguments);
      setFrequency(body);

      const scan = await apiPost('/scans', {
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
    } catch (e: any) {
      setErrors({
        global: e.message ?? e.toString()
      });
      setSnackbarMsg(`Scan creation failed: ${e.message ?? e.toString()}`);
      setSnackbarOpen(true);
      console.log(e);
    }
  };

  const invokeScheduler = async () => {
    setErrors({ ...errors, scheduler: '' });
    try {
      await apiPost('/scheduler/invoke', { body: {} });
    } catch (e) {
      console.error(e);
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
      await apiPost(`/scans/${id}/run`, { body: {} });
    } catch (e) {
      console.error(e);
      setErrors({ ...errors, scheduler: 'Run failed.' });
    }
    await invokeScheduler();
  };

  const handleSubmit = () => {
    runScan(selectedId);
    setOpen(false);
  };
  const handleClose = () => {
    setOpen(false);
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

  const handleClick = () => {
    setOpen(true);
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
              handleClick();
            }}
          >
            <FaPlayCircle />
          </IconButton>
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
      minWidth: 100,
      flex: 1,
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
      minWidth: 100,
      flex: 1,
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
              deleteModalRef.current?.toggleModal(undefined, true);
              setSelectedId(cellValues.row.id);
              setSelectedName(cellValues.row.name);
            }}
          >
            <FaTimes />
          </IconButton>
        );
      }
    },
    {
      field: 'description',
      headerName: 'Description',
      minWidth: 250,
      flex: 5,
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
  // const importScanButton = (
  //   <MuiButton
  //     size="small"
  //     sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
  //     startIcon={<Publish />}
  //     onClick={() => {
  //       setDialogOpen(true);
  //     }}
  //   >
  //     Import
  //   </MuiButton>
  // );

  //To-do: Add a button to toolbar to add scans
  // const addScanButton = (
  //   <MuiButton
  //     size="small"
  //     sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
  //     startIcon={<Add />}
  //     onClick={() => {
  //       addScanModalRef.current?.toggleModal(undefined, true);
  //     }}
  //   >
  //     Add Scan
  //   </MuiButton>
  // );

  //To-do: Dialogs/Modals need to be built for Import and Add Scan. Export is already handled by MUI DataGrid.

  return (
    <>
      <Box mb={3}>
        <Dialog
          open={open}
          onClose={handleClose}
          aria-labelledby="run-scan-dialog-title"
          aria-describedby="run-scan-dialog-description"
        >
          <DialogTitle id="run-scan-dialog-title">Confirmation</DialogTitle>
          <DialogContent>
            <DialogContentText id="run-scan-dialog-description">
              Are you sure you would like to run the {selectedName} scan?
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <MuiButton
              onClick={handleClose}
              aria-label="Cancel running the scan"
            >
              Cancel
            </MuiButton>
            <MuiButton
              variant="contained"
              onClick={handleSubmit}
              aria-label="Confirm and run the scan"
            >
              Run
            </MuiButton>
          </DialogActions>
        </Dialog>
        <Paper elevation={0}>
          {scans?.length === 0 ? (
            <Alert severity="info">No scans found</Alert>
          ) : (
            <DataGrid
              rows={scansRows}
              columns={scansCols}
              //To-do: re-enable Custom Toolbar to handle scan Create, Export, Import,
              // slots={{ toolbar: CustomToolbar }}
              // slotProps={{
              //   toolbar: { children: [importScanButton, addScanButton] }
              // }}
            />
          )}
        </Paper>
      </Box>
      <Button type="submit" outline onClick={invokeScheduler}>
        Manually run scheduler
      </Button>
      {errors.scheduler && <p className={classes.error}>{errors.scheduler}</p>}
      <h2>Add a scan</h2>
      {errors.global && <p className={classes.error}>{errors.global}</p>}
      <ScanForm
        organizationOption={organizationOptions}
        tags={tags}
        propValues={values}
        onSubmit={onSubmit}
        type="create"
        scanSchema={scanSchema}
      ></ScanForm>
      {/* To-Do: Undefined props are needed to avoid errors. This Modal needs to
      be replaced with a MUI Dialog. */}
      <Modal
        ref={deleteModalRef}
        id="deleteModal"
        placeholder={undefined}
        onPointerEnterCapture={undefined}
        onPointerLeaveCapture={undefined}
      >
        <ModalHeading>Delete scan?</ModalHeading>
        <p>
          Are you sure you would like to delete the <code>{selectedName}</code>{' '}
          scan?
        </p>
        <ModalFooter>
          <ButtonGroup>
            <ModalToggleButton
              modalRef={deleteModalRef}
              closer
              onClick={() => {
                deleteRow(selectedId);
              }}
            >
              Delete
            </ModalToggleButton>
            <ModalToggleButton
              modalRef={deleteModalRef}
              closer
              unstyled
              className="padding-105 text-center"
            >
              Cancel
            </ModalToggleButton>
          </ButtonGroup>
        </ModalFooter>
      </Modal>
      <Snackbar
        open={snackbarOpen}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbarMsg.includes('failed') ? 'error' : 'success'}
          sx={{ width: '100%' }}
        >
          <span tabIndex={0}>{snackbarMsg}</span>
        </Alert>
      </Snackbar>
    </>
  );
};

export default ScansView;
