import React, { useCallback, useEffect, useState } from 'react';
import { logger } from '@/utils/logger';
import { useAuthContext } from 'context';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { ENDPOINTS } from '@/constants/endpoints';

interface Queue {
  name: string;
  messages_available: number;
  messages_in_flight: number;
  messages_delayed: number;
}

const QueueMonitorView: React.FC = () => {
  const { apiPost } = useAuthContext();
  const [queues, setQueues] = useState<Queue[]>([]);
  const [errors, setErrors] = useState<{ global?: string }>({});

  const fetchQueues = useCallback(async () => {
    try {
      const { result } = await apiPost(ENDPOINTS.QUEUES_SEARCH, { body: {} });

      // Ensure each queue has a unique 'id' (using its name)
      const queuesWithId = result.map((queue: Queue) => ({
        ...queue,
        id: queue.name // Use the queue name as a unique ID
      }));

      setQueues(queuesWithId);
    } catch (e) {
      logger.error(e);
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
          aria-label={`Messages Available for ${cellValues.row.id}: ${cellValues.row.messages_available}`}
        >
          {cellValues.row.messages_available}
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
          aria-label={`Messages In-Flight for ${cellValues.row.id}: ${cellValues.row.messages_in_flight}`}
        >
          {cellValues.row.messages_in_flight}
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
          aria-label={`Messages Delayed for ${cellValues.row.id}: ${cellValues.row.messages_delayed}`}
        >
          {cellValues.row.messages_delayed}
        </Box>
      )
    }
  ];

  return (
    <>
      {errors.global && <Alert severity="error">{errors.global}</Alert>}
      <Stack direction="row" justifyContent="flex-end" mb={2}>
        <Button variant="contained" onClick={fetchQueues}>
          Refresh
        </Button>
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
