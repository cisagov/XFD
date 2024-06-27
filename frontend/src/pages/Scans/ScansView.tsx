import classes from './Scans.module.scss';
import React, { useCallback, useRef, useState } from 'react';
import {
  Button,
  Modal,
  ButtonGroup,
  ModalFooter,
  ModalHeading,
  ModalRef
} from '@trussworks/react-uswds';
import { ModalToggleButton } from 'components';
import { ImportExport } from 'components';
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
import { Alert, Box, IconButton, Paper } from '@mui/material';
//Needed for the CustomToolbar:
// import { Button as MuiButton } from '@mui/material';
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
  lastRun: string;
  description: string;
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

  const [values] = useState<ScanFormValues>({
    name: 'censys',
    arguments: '{}',
    organizations: [],
    frequency: 1,
    frequencyUnit: 'minute',
    isGranular: false,
    isUserModifiable: false,
    isSingleScan: false,
    tags: []
  });

  const fetchScans = useCallback(async () => {
    try {
      const { scans, organizations, schema } = await apiGet<{
        scans: Scan[];
        organizations: Organization[];
        schema: ScanSchema;
      }>('/scans/');
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
          e.status === 422 ? 'Unable to delete scan' : e.message ?? e.toString()
      });
      console.log(e);
    }
  };

  const onSubmit = async (body: ScanFormValues) => {
    try {
      // For now, parse the arguments as JSON. We'll want to add a GUI for this in the future
      body.arguments = JSON.parse(body.arguments);
      setFrequency(body);

      const scan = await apiPost('/scans/', {
        body: {
          ...body,
          organizations: body.organizations
            ? body.organizations.map((e) => e.value)
            : [],
          tags: body.tags ? body.tags.map((e) => ({ id: e.value })) : []
        }
      });
      setScans(scans.concat(scan));
    } catch (e: any) {
      setErrors({
        global: e.message ?? e.toString()
      });
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

  //Code for new table//

  React.useEffect(() => {
    fetchScans();
  }, [fetchScans]);

  const scansRows: ScansRow[] = scans.map((scan) => {
    return {
      id: scan.id,
      name: scan.name,
      tags: scan.tags.map((tag) => tag.name).join(', '),
      mode:
        scanSchema[scan.name] && scanSchema[scan.name].isPassive
          ? 'Passive'
          : 'Active',
      frequency: scan.frequency,
      lastRun:
        !scan.lastRun ||
        new Date(scan.lastRun).getTime() === new Date(0).getTime()
          ? 'None'
          : `${formatDistanceToNow(parseISO(scan.lastRun))} ago`,
      description: scanSchema[scan.name]?.description
    };
  });

  const scansCols: GridColDef[] = [
    {
      field: 'run',
      headerName: 'Run',
      minWidth: 50,
      flex: 0.5,
      disableExport: true,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            aria-label={`Run scan for ${cellValues.row.name}`}
            tabIndex={cellValues.tabIndex}
            color="primary"
            onClick={() => {
              runScan(cellValues.row.id);
            }}
          >
            <FaPlayCircle />
          </IconButton>
        );
      }
    },
    { field: 'name', headerName: 'Name', minWidth: 100, flex: 1 },
    { field: 'tags', headerName: 'Tags', minWidth: 100, flex: 1 },
    { field: 'mode', headerName: 'Mode', minWidth: 100, flex: 1 },
    { field: 'frequency', headerName: 'Frequency', minWidth: 100, flex: 1 },
    { field: 'lastRun', headerName: 'Last Run', minWidth: 100, flex: 1 },
    {
      field: 'delete',
      headerName: 'Delete',
      minWidth: 50,
      flex: 1,
      disableExport: true,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            aria-label={`Delete scan for ${cellValues.row.name}`}
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
    { field: 'description', headerName: 'Description', minWidth: 250, flex: 5 }
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
      <ImportExport<Scan>
        name="scans"
        fieldsToImport={['name', 'arguments', 'frequency']}
        onImport={async (results) => {
          // TODO: use a batch call here instead.
          const createdScans = [];
          for (const result of results) {
            createdScans.push(
              await apiPost('/scans/', {
                body: {
                  ...result,
                  // These fields are initially parsed as strings, so they need
                  // to be converted to objects.
                  arguments: JSON.parse(
                    (result.arguments as unknown as string) || ''
                  )
                }
              })
            );
          }
          setScans(scans.concat(...createdScans));
        }}
      />

      <Modal ref={deleteModalRef} id="deleteModal">
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
    </>
  );
};

export default ScansView;
