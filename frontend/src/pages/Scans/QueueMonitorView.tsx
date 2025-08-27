import React, { useCallback, useEffect, useState } from 'react';
import { useAuthContext } from 'context';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { Stack } from '@mui/system';
import { Alert, Box, Button as MuiButton, Paper } from '@mui/material';

interface Queue {
  name: string;
  messagesAvailable: number;
  messagesInFlight: number;
  messagesDelayed: number;
}

const QueueMonitorView: React.FC = () => {
  const { apiPost } = useAuthContext();
  const [queues, setQueues] = useState<Queue[]>([]);
  const [errors, setErrors] = useState<{ global?: string }>({});

  const fetchQueues = useCallback(async () => {
    try {
      const { result } = await apiPost('/queues/search', { body: {} });

      // Ensure each queue has a unique 'id' (using its name)
      const queuesWithId = result.map((queue: Queue) => ({
        ...queue,
        id: queue.name // Use the queue name as a unique ID
      }));

      setQueues(queuesWithId);
    } catch (e) {
      console.error(e);
      setErrors({ global: 'Failed to fetch queue data.' });
    }
  }, [apiPost]);

  useEffect(() => {
    fetchQueues();
  }, [fetchQueues]);

  const queueColumns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Queue Name',
      flex: 2,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component={'span'}
          aria-label={`Queue Name for ${cellValues.row.id}: ${cellValues.row.name}`}
        >
          {cellValues.row.name}
        </Box>
      )
    },
    {
      field: 'messages_available',
      headerName: 'Available',
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component={'span'}
          aria-label={`Messages Available for ${cellValues.row.id}: ${cellValues.row.messagesAvailable}`}
        >
          {cellValues.row.messagesAvailable}
        </Box>
      )
    },
    {
      field: 'messages_in_flight',
      headerName: 'In-Flight',
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component={'span'}
          aria-label={`Messages In-Flight for ${cellValues.row.id}: ${cellValues.row.messagesInFlight}`}
        >
          {cellValues.row.messagesInFlight}
        </Box>
      )
    },
    {
      field: 'messages_delayed',
      headerName: 'Delayed',
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component={'span'}
          aria-label={`Messages Delayed for ${cellValues.row.id}: ${cellValues.row.messagesDelayed}`}
        >
          {cellValues.row.messagesDelayed}
        </Box>
      )
    }
  ];

  return (
    <>
      {errors.global && <Alert severity="error">{errors.global}</Alert>}
      <Stack direction="row" justifyContent="flex-end" mb={2}>
        <MuiButton variant="contained" onClick={fetchQueues}>
          Refresh
        </MuiButton>
      </Stack>
      <Paper elevation={2}>
        <DataGrid
          rows={queues}
          columns={queueColumns}
          pageSizeOptions={[10, 25, 100]}
          disableRowSelectionOnClick
        />
      </Paper>
    </>
  );
};

export default QueueMonitorView;
