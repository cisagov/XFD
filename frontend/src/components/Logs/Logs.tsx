import {
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import CancelIcon from '@mui/icons-material/Cancel';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { Box } from '@mui/system';
import {
  DataGrid,
  GridColDef,
  GridFilterItem,
  GridRenderEditCellParams
} from '@mui/x-data-grid';
import { useAuthContext } from 'context';
import { format, parseISO } from 'date-fns';
import React, { FC, useCallback, useEffect, useState } from 'react';
import CustomToolbar from 'components/DataGrid/CustomToolbar';

import { toZonedTime } from 'date-fns-tz';

interface LogsProps {}

interface LogDetails {
  id?: number;
  created_at: string;
  event_type: string;
  result: string;
  payload: any;
}

const PAGE_SIZE = 15;

export const Logs: FC<LogsProps> = () => {
  const { apiPost } = useAuthContext();
  const [filters, setFilters] = useState<Array<GridFilterItem>>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogDetails, setDialogDetails] = useState<LogDetails | null>(null);
  const [logs, setLogs] = useState<{
    count: number;
    result: LogDetails[];
  }>({
    count: 0,
    result: []
  });

  const fetchLogs = useCallback(async () => {
    const fieldMap: Record<string, string> = {
      event_type: 'event_type',
      acting_user_name: 'payload.user_performed_assignment.full_name',
      acting_user_email: 'payload.user_performed_assignment.email',
      acted_on_user_name: 'payload.user.full_name',
      acted_on_user_email: 'payload.user.email',
      organization: 'payload.organization.name',
      region: 'payload.user_performed_assignment.region_id',
      role: 'payload.role',
      state: 'payload.state',
      user_type: 'payload.user.user_type',
      created_at: 'timestamp',
      result: 'result'
    };

    const tableFilters = filters.reduce(
      (acc, cur) => {
        const field = fieldMap[cur.field] || cur.field;
        let value = cur.value;

        // Convert local time to UTC ISO string for timestamp filter
        if (field === 'timestamp' && typeof value === 'string' && value) {
          const localDate = new Date(value);
          value = localDate.toISOString().slice(0, 16);
        }

        acc[field] = { value, operator: cur.operator };
        return acc;
      },
      {} as { [key: string]: { value: any; operator: any } }
    );

    const endpoint =
      Object.keys(tableFilters).length > 0
        ? '/logs/filtered-search'
        : '/logs/search';

    try {
      const body =
        endpoint === '/logs/filtered-search'
          ? { page: 1, page_size: PAGE_SIZE, filters: tableFilters }
          : {};
      const results = await apiPost(endpoint, { body });

      if (!results || !Array.isArray(results.result)) {
        console.error('Invalid response format:', results);
        setLogs({ count: 0, result: [] });
        return;
      }

      const rowsWithId = results.result.map(
        (log: LogDetails, index: number) => ({
          ...log,
          id: index
        })
      );

      setLogs({ count: results.count, result: rowsWithId });
    } catch (e) {
      console.error(`Fetch logs error from ${endpoint}:`, e);
      setLogs({ count: 0, result: [] });
    }
  }, [apiPost, filters]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const formatTimestamp = (timestamp: string): string | null => {
    if (!timestamp) return 'N/A';
    try {
      const utcDate = parseISO(timestamp);
      const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const zonedDate = toZonedTime(utcDate, timeZone);
      return format(zonedDate, 'MM/dd/yyyy hh:mm a');
    } catch (error) {
      console.error('Error parsing date:', error);
      return null;
    }
  };

  const logCols: GridColDef[] = [
    {
      field: 'event_type',
      headerName: 'Event',
      minWidth: 100,
      flex: 1.25,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Event Type for Log ${cellValues.row.id}: ${cellValues.row.event_type}`}
          >
            {cellValues.row.event_type}
          </Box>
        );
      }
    },
    {
      field: 'acting_user_name',
      headerName: 'Acting User Name',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        const p =
          cellValues.row.payload?.user_performed_assignment ||
          cellValues.row.payload?.user_performed_removal ||
          cellValues.row.payload?.user_performed_approval ||
          cellValues.row.payload?.user_performed_invite;
        return (
          <Box
            component={'span'}
            aria-label={`Acting User Name for Log ${cellValues.row.id}: ${p?.full_name || 'N/A'}`}
          >
            {p?.full_name || 'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'acting_user_email',
      headerName: 'Acting User Email',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        const p =
          cellValues.row.payload?.user_performed_assignment ||
          cellValues.row.payload?.user_performed_removal ||
          cellValues.row.payload?.user_performed_approval ||
          cellValues.row.payload?.user_performed_invite;
        return (
          <Box
            component={'span'}
            aria-label={`Acting User Email for Log ${cellValues.row.id}: ${p?.email || 'N/A'}`}
          >
            {p?.email || 'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'acted_on_user_name',
      headerName: 'Acted-on User Name',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        const u =
          cellValues.row.payload?.user ||
          cellValues.row.payload?.removal_result?.role_deleted?.user ||
          cellValues.row.payload?.user_to_approve ||
          cellValues.row.payload?.approval_results?.role_deleted?.user;
        return (
          <Box
            component={'span'}
            aria-label={`Acted-On User Name for Log ${cellValues.row.id}: ${u?.full_name || 'N/A'}`}
          >
            {u?.full_name || 'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'acted_on_user_email',
      headerName: 'Acted-on User Email',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        const u =
          cellValues.row.payload?.user ||
          cellValues.row.payload?.removal_result?.role_deleted?.user ||
          cellValues.row.payload?.user_to_approve ||
          cellValues.row.payload?.approval_results?.role_deleted?.user;
        return (
          <Box
            component={'span'}
            aria-label={`Acted-On User Email for Log ${cellValues.row.id}: ${u?.email || 'N/A'}`}
          >
            {u?.email || 'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'organization',
      headerName: 'Organization',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Organization for Log ${cellValues.row.id}: ${cellValues.row.payload?.organization?.name || cellValues.row.payload?.from_organization?.name || 'N/A'}`}
          >
            {cellValues.row.payload?.organization?.name ||
              cellValues.row.payload?.from_organization?.name ||
              'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'region',
      headerName: 'Region',
      minWidth: 100,
      flex: 0.75,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Region for Log ${cellValues.row.id}: ${cellValues.row.payload?.user_performed_assignment?.region_id || cellValues.row.payload?.user_performed_removal?.region_id || cellValues.row.payload?.user_performed_approval?.region_id || cellValues.row.payload?.user_performed_invite?.region_id || 'N/A'}`}
          >
            {cellValues.row.payload?.user_performed_assignment?.region_id ||
              cellValues.row.payload?.user_performed_removal?.region_id ||
              cellValues.row.payload?.user_performed_approval?.region_id ||
              cellValues.row.payload?.user_performed_invite?.region_id ||
              'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'role',
      headerName: 'Role',
      minWidth: 100,
      flex: 0.75,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Role for Log ${cellValues.row.id}: ${cellValues.row.payload?.role || 'N/A'}`}
          >
            {cellValues.row.payload?.role || 'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'state',
      headerName: 'State',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`State for Log ${cellValues.row.id}: ${
              cellValues.row.payload?.state ||
              cellValues.row.payload?.user_performed_assignment?.state ||
              cellValues.row.payload?.user_performed_removal?.state ||
              cellValues.row.payload?.user_performed_approval?.state ||
              cellValues.row.payload?.user_performed_invite?.state ||
              cellValues.row.payload?.user?.state ||
              'N/A'
            }`}
          >
            {cellValues.row.payload?.state ||
              cellValues.row.payload?.user_performed_assignment?.state ||
              cellValues.row.payload?.user_performed_removal?.state ||
              cellValues.row.payload?.user_performed_approval?.state ||
              cellValues.row.payload?.user_performed_invite?.state ||
              cellValues.row.payload?.user?.state ||
              'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'user_type',
      headerName: 'User Type',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`User Type for Log ${cellValues.row.id}: ${cellValues.row.payload?.user?.user_type || cellValues.row.payload?.user_to_approve?.user_type || 'N/A'}`}
          >
            {cellValues.row.payload?.user?.user_type ||
              cellValues.row.payload?.user_to_approve?.user_type ||
              'N/A'}
          </Box>
        );
      }
    },
    {
      field: 'created_at',
      headerName: 'Timestamp',
      minWidth: 100,
      flex: 1.25,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        return (
          <Box
            component={'span'}
            aria-label={`Timestamp for Log ${cellValues.row.id}: ${cellValues.value}`}
          >
            {formatTimestamp(cellValues.row.created_at)}
          </Box>
        );
      }
    },
    {
      field: 'result',
      headerName: 'Result',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderEditCellParams) => {
        const isSuccess = cellValues.row.result === 'success';
        return (
          <Box
            component={'span'}
            aria-label={`Result for Log ${cellValues.row.id}: ${cellValues.row.result}`}
            sx={{ display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            {isSuccess ? (
              <CheckCircleIcon sx={{ color: '#6c757d' }} />
            ) : (
              <CancelIcon sx={{ color: '#6c757d' }} />
            )}
            {cellValues.row.result}
          </Box>
        );
      }
    },
    {
      field: 'details',
      headerName: 'Payload',
      maxWidth: 70,
      flex: 0.5,
      renderCell: (cellValues: GridRenderEditCellParams) => (
        <IconButton
          aria-label={`Details for Log ${cellValues.row.id}`}
          tabIndex={cellValues.tabIndex}
          color="primary"
          onClick={() => {
            setOpenDialog(true);
            setDialogDetails(cellValues.row);
          }}
        >
          <OpenInNewIcon />
        </IconButton>
      )
    }
  ];

  return (
    <Box display="flex">
      <Paper elevation={2} sx={{ width: '100%', minHeight: '200px' }}>
        <DataGrid
          rows={logs.result}
          columns={logCols}
          filterMode="server"
          slots={{
            toolbar: CustomToolbar
          }}
          slotProps={{
            basePopper: {
              placement: 'bottom-start'
            }
          }}
          onFilterModelChange={(model) => {
            setFilters(model.items);
          }}
          initialState={{
            pagination: { paginationModel: { pageSize: PAGE_SIZE } },
            sorting: {
              sortModel: [{ field: 'created_at', sort: 'desc' }]
            },
            columns: {
              columnVisibilityModel: {
                role: false,
                region: false,
                state: false,
                acting_user_email: false,
                acted_on_user_email: false
              }
            }
          }}
          pageSizeOptions={[15, 30, 50, 100]}
          disableRowSelectionOnClick
          showToolbar
        />
      </Paper>
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
              backgroundColor: 'black',
              color: 'white',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
          >
            <pre>{JSON.stringify(dialogDetails?.payload, null, 2)}</pre>
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
};
