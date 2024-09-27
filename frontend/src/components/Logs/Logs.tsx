import {
  Dialog,
  DialogContent,
  DialogTitle,
  Icon,
  IconButton,
  Paper
} from '@mui/material';
import { Box } from '@mui/system';
import {
  DataGrid,
  GridColDef,
  GridFilterItem,
  GridRenderEditCellParams,
  GridToolbar,
  GridToolbarColumnsButton,
  GridToolbarDensitySelector,
  GridToolbarFilterButton
} from '@mui/x-data-grid';
import { useAuthContext } from 'context';
import { differenceInCalendarDays, parseISO } from 'date-fns';
import React, { FC, useCallback, useEffect, useState } from 'react';

interface LogsProps {}

interface LogDetails {
  createdAt: string;
  eventType: string;
  result: string;
  payload: string;
}

const CustomToolbar = () => {
  return (
    <GridToolbar>
      <GridToolbarColumnsButton />
      <GridToolbarFilterButton />
      <GridToolbarDensitySelector />
    </GridToolbar>
  );
};

export const Logs: FC<LogsProps> = () => {
  const { apiPost } = useAuthContext();
  const [filters, setFilters] = useState<Array<GridFilterItem>>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogDetails, setDialogDetails] = useState<
    (LogDetails & { id: number }) | null
  >(null);
  const [logs, setLogs] = useState<{
    count: Number;
    result: Array<LogDetails>;
  }>({
    count: 0,
    result: []
  });

  const fetchLogs = useCallback(async () => {
    const tableFilters = filters.reduce(
      (acc: { [key: string]: { value: any; operator: any } }, cur) => {
        return {
          ...acc,
          [cur.field]: {
            value: cur.value,
            operator: cur.operator
          }
        };
      },
      {}
    );
    const results = await apiPost('/logs/search', {
      body: {
        ...tableFilters
      }
    });
    setLogs(results);
  }, [apiPost, filters]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const logCols: GridColDef[] = [
    {
      field: 'eventType',
      headerName: 'Event',
      minWidth: 100,
      flex: 1
    },
    {
      field: 'result',
      headerName: 'Result',
      minWidth: 100,
      flex: 1
    },
    {
      field: 'createdAt',
      headerName: 'Timestamp',
      type: 'dateTime',
      minWidth: 100,
      flex: 1,
      valueFormatter: (e) => {
        return `${differenceInCalendarDays(
          Date.now(),
          parseISO(e.value)
        )} days ago`;
      }
    },
    {
      field: 'payload',
      headerName: 'Payload',
      description: 'Click any payload cell to expand.',
      sortable: false,
      minWidth: 300,
      flex: 2,
      renderCell: (cellValues) => {
        return (
          <Box
            sx={{
              fontSize: '12px',
              padding: 0,
              margin: 0,
              backgroundColor: 'black',
              color: 'white',
              width: '100%'
            }}
          >
            <pre>{JSON.stringify(cellValues.row.payload, null, 2)}</pre>
          </Box>
        );
      },
      valueFormatter: (e) => {
        return JSON.stringify(e.value, null, 2);
      }
    },
    {
      field: 'details',
      headerName: 'Details',
      maxWidth: 70,
      flex: 1,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        return (
          <IconButton
            aria-label={`Details for scan task ${cellValues.row.id}`}
            tabIndex={cellValues.tabIndex}
            color="primary"
            onClick={() => {
              setOpenDialog(true);
              setDialogDetails(cellValues.row);
            }}
          >
            <Icon>info</Icon>
          </IconButton>
        );
      }
    }
  ];

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  return (
    <Box>
      <Paper elevation={2} sx={{ width: '100%' }}>
        <DataGrid
          rows={logs.result}
          columns={logCols}
          filterMode="server"
          slots={{
            toolbar: CustomToolbar
          }}
          slotProps={{ toolbar: { multifilter: true } }}
          onFilterModelChange={(model) => {
            setFilters(model.items);
          }}
        />
        <Dialog
          open={openDialog}
          onClose={() => setOpenDialog(false)}
          scroll="paper"
          fullWidth
          maxWidth="lg"
        >
          <DialogTitle>Payload Details</DialogTitle>
          <DialogContent>
            <Box
              sx={{
                fontSize: '12px',
                padding: 2,
                margin: 0,
                backgroundColor: 'black',
                color: 'white',
                width: '100%'
              }}
            >
              <pre>{JSON.stringify(dialogDetails?.payload, null, 2)}</pre>
            </Box>
          </DialogContent>
        </Dialog>
      </Paper>
    </Box>
  );
};
