import { Box } from '@mui/system';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useAuthContext } from 'context';
import { differenceInCalendarDays, parseISO } from 'date-fns';
import React, { FC, useCallback, useEffect, useState } from 'react';

interface LogsProps {}

export const Logs: FC<LogsProps> = () => {
  const { apiGet } = useAuthContext();
  const [logs, setLogs] = useState<{ count: Number; result: [] }>({
    count: 0,
    result: []
  });

  const fetchLogs = useCallback(async () => {
    const results = await apiGet('/logs');
    setLogs(results);
  }, []);

  useEffect(() => {
    fetchLogs();
  }, []);

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
    }
  ];

  return (
    <Box>
      <DataGrid rows={logs.result} columns={logCols} />
    </Box>
  );
};
