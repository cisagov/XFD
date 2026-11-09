// React
import React, { useCallback, useEffect, useState } from 'react';

// MUI Components
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import type {
  GridColDef,
  GridFilterModel,
  GridRenderCellParams
} from '@mui/x-data-grid';

// Components
import CustomDataGrid from '@/components/DataGrid/CustomDataGrid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';

// Context & Hooks
import { useAuthContext } from 'context';

// Constants & Utils
import { ENDPOINTS } from '@/constants/endpoints';
import {
  DATA_GRID_PAGE_SIZE_OPTIONS,
  DEFAULT_DATA_GRID_PAGE_SIZE
} from '@/constants/dataGrid';
import { logger } from '@/utils/logger';
import { cleanFilterModelItems, isFilterModelEmpty } from '@/utils/tableUtils';
import { formatDisplayValue } from 'utils/stringUtils';
import { textFilterOperators } from '@/utils/transformTableData';

interface Queue {
  name: string;
  messages_available: number;
  messages_in_flight: number;
  messages_delayed: number;
}

type QueueSearchResponse = {
  result: Queue[];
  count: number;
};

const QueueMonitorView: React.FC = () => {
  const { apiPost } = useAuthContext();
  const [queues, setQueues] = useState<Queue[]>([]);
  const [errors, setErrors] = useState<{ global?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [filterModel, setFilterModel] = useState<GridFilterModel>({
    items: []
  });
  const [hasActiveFilters, setHasActiveFilters] = useState(false);

  const fetchQueues = useCallback(async () => {
    setIsLoading(true);
    setErrors({});
    try {
      const { result } = await apiPost<QueueSearchResponse>(
        ENDPOINTS.QUEUES_SEARCH,
        { body: {} }
      );

      // Ensure each queue has a unique 'id' (using its name)
      const queuesWithId = result.map((queue: Queue) => ({
        ...queue,
        id: queue.name // Use the queue name as a unique ID
      }));

      setQueues(queuesWithId);
    } catch (e) {
      logger.error(e);
      setErrors({ global: 'Failed to fetch queue data.' });
    } finally {
      setIsLoading(false);
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
      filterOperators: textFilterOperators,
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
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component={'span'}
          aria-label={`Messages Available for ${cellValues.row.id}: ${cellValues.row.messages_available}`}
        >
          {formatDisplayValue(cellValues.row.messages_available)}
        </Box>
      )
    },
    {
      field: 'messages_in_flight',
      headerName: 'In-Flight',
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component={'span'}
          aria-label={`Messages In-Flight for ${cellValues.row.id}: ${cellValues.row.messages_in_flight}`}
        >
          {formatDisplayValue(cellValues.row.messages_in_flight)}
        </Box>
      )
    },
    {
      field: 'messages_delayed',
      headerName: 'Delayed',
      flex: 1,
      filterOperators: textFilterOperators,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component={'span'}
          aria-label={`Messages Delayed for ${cellValues.row.id}: ${cellValues.row.messages_delayed}`}
        >
          {formatDisplayValue(cellValues.row.messages_delayed)}
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
        <CustomDataGrid
          rows={queues}
          columns={queueColumns}
          loading={isLoading}
          filterModel={filterModel}
          onFilterModelChange={(model) => {
            const cleanedModel = cleanFilterModelItems(model, filterModel);
            setFilterModel(cleanedModel);
            setHasActiveFilters(!isFilterModelEmpty(cleanedModel));
          }}
          slots={{ toolbar: CustomToolbar }}
          slotProps={{
            toolbar: {
              disableExport: true,
              exportTitle: 'Queue Monitor',
              hasActiveFilters
            } as any,
            basePopper: {
              placement: 'bottom-start'
            }
          }}
          initialState={{
            pagination: {
              paginationModel: { pageSize: DEFAULT_DATA_GRID_PAGE_SIZE }
            }
          }}
          pageSizeOptions={DATA_GRID_PAGE_SIZE_OPTIONS}
          disableRowSelectionOnClick
          showToolbar
        />
      </Paper>
    </>
  );
};

export default QueueMonitorView;
