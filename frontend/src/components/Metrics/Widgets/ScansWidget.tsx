import React, {
  useEffect,
  useCallback,
  useState,
  useMemo,
  useRef
} from 'react';
import { Box, Paper } from '@mui/material';
import {
  DataGrid,
  GridColDef,
  GridRenderCellParams,
  GridCellParams
} from '@mui/x-data-grid';
import { SparkLineChart } from '@mui/x-charts/SparkLineChart';
import dayjs from 'dayjs';
import { visuallyHidden } from '@mui/utils';
import { useAuthContext } from 'context';
import * as MetricsStyles from '../style';
import InfoLabel from 'components/Dashboard/InfoLabel';
import {
  ScanDetails,
  ScanSummaries,
  OrgCountByStatus,
  ScanSummary
} from '../../../types/metrics';

const scanMetricsTooltip = [
  {
    id: 'Scan Metrics',
    content:
      'This widget shows success/failure metrics for non-global scans over the displayed time period (default is 7 days). ' +
      'The "Scan Result Summary" table lists scans and . The “Total Orgs” column shows the total number of organizations that the scan was run against. ' +
      'Each status code column (e.g. 200, 404, 500) shows how many unique organizations returned that status code at least once within the time window. ' +
      'The “HTTP Status Trends" table appears when you select a scan. It shows daily trends as small line charts (sparklines) for each status code, over the date range. ' +
      'Status codes follow the categories defined in RFC 9110 (HTTP Semantics): 1xx = informational responses, 2xx = successful responses, 3xx = redirects, 4xx = client errors, and 5xx = server errors. '
  }
];

const generateDateRange = (days: number): string[] => {
  const today = dayjs().startOf('day');
  return Array.from({ length: days }, (_, i) =>
    today.subtract(days - 1 - i, 'day').format('YYYY-MM-DD')
  );
};

const STATUS_COLORS: Record<number, string> = {
  1: '#5c5c5c', // Gray for informational (1xx)
  2: '#1a7f37', // Green for success (2xx)
  3: '#125ea4', // Blue for redirects (3xx)
  4: '#c75200', // Orange for client errors (4xx)
  5: '#a51414' // Red for server errors (5xx)
};

const getStatusColor = (status: number): string => {
  const category = Math.floor(status / 100);
  return STATUS_COLORS[category] || '#5c5c5c';
};

const ScansWidget: React.FC = () => {
  const { apiGet } = useAuthContext();
  const [scanSummaries, setScanSummaries] = useState<ScanSummaries | null>(
    null
  );
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [scanDetails, setScanDetails] = useState<ScanDetails | null>(null);

  const { cardRoot, cardSmall, header, body } = MetricsStyles.classesMetrics;

  // Focus target for details region (Chart 2)
  const detailsRegionRef = useRef<HTMLDivElement | null>(null);

  const fetchScanSummaries = useCallback(async () => {
    const result = await apiGet('/metrics/scans');
    setScanSummaries(result || null);
  }, [apiGet]);

  const fetchScanDetails = useCallback(
    async (scanId: string) => {
      const result = await apiGet('/metrics/scans/' + scanId);
      setScanDetails(result || null);
    },
    [apiGet]
  );

  useEffect(() => {
    fetchScanSummaries();
  }, [fetchScanSummaries]);

  // When details load, move keyboard focus to the details region (Chart 2)
  useEffect(() => {
    if (scanDetails && detailsRegionRef.current) {
      requestAnimationFrame(function () {
        if (detailsRegionRef.current) {
          detailsRegionRef.current.focus();
        }
      });
    }
  }, [scanDetails]);

  const handleScanClick = (scanId: string) => {
    setSelectedScanId(scanId);
    fetchScanDetails(scanId);
  };

  // =========================
  // Summary Grid (top table)
  // =========================
  const allStatusCodes: number[] = useMemo(() => {
    return scanSummaries?.scans
      ? Array.from(
          new Set(
            scanSummaries.scans.flatMap((scan: ScanSummary) =>
              scan.org_counts_by_status.map(
                (status: OrgCountByStatus) => status.http_status
              )
            )
          )
        ).sort((a, b) => a - b)
      : [];
  }, [scanSummaries]);

  const metricsWindowDays = useMemo(() => {
    return scanSummaries?.metrics_window_days ?? 'N';
  }, [scanSummaries]);

  type SummaryRow = {
    id: string;
    name: string;
    total_orgs: number;
    // dynamic status code fields, e.g., s200, s404
    [key: string]: any;
  };

  const summaryRows: SummaryRow[] = useMemo(() => {
    if (!scanSummaries?.scans) return [];
    return scanSummaries.scans.map((scan) => {
      const row: SummaryRow = {
        id: scan.id,
        name: scan.name,
        total_orgs: scan.total_orgs
      };
      scan.org_counts_by_status.forEach((s) => {
        row['s' + s.http_status] = s.org_count;
      });
      // Ensure all codes exist so columns line up
      allStatusCodes.forEach((code) => {
        const key = 's' + code;
        if (typeof row[key] === 'undefined') row[key] = 0;
      });
      return row;
    });
  }, [scanSummaries, allStatusCodes]);

  const summaryColumns: GridColDef[] = useMemo(() => {
    const base: GridColDef[] = [
      {
        field: 'name',
        headerName: 'Scan Name',
        minWidth: 140,
        flex: 1.6,
        renderCell: (params: GridRenderCellParams<SummaryRow>) => (
          <Box component="span" aria-label={'Scan name ' + params.row.name}>
            {params.row.name}
          </Box>
        )
      },
      {
        field: 'total_orgs',
        headerName: 'Total Orgs',
        minWidth: 110,
        flex: 0.7,
        align: 'center',
        headerAlign: 'center',
        renderCell: (params: GridRenderCellParams<SummaryRow>) => (
          <Box
            component="span"
            aria-label={
              'Total organizations ' +
              params.row.total_orgs +
              ' for scan ' +
              params.row.name
            }
          >
            {params.row.total_orgs}
          </Box>
        )
      }
    ];

    const statusCols: GridColDef[] = allStatusCodes.map((code) => ({
      field: 's' + code,
      headerName: String(code),
      minWidth: 80,
      flex: 0.6,
      align: 'center',
      headerAlign: 'center',
      renderCell: (params: GridRenderCellParams<SummaryRow>) => (
        <Box
          component="span"
          aria-label={
            'HTTP status ' +
            code +
            ' organization count ' +
            params.value +
            ' for scan ' +
            params.row.name
          }
        >
          {params.value}
        </Box>
      )
    }));

    return [...base, ...statusCols];
  }, [allStatusCodes]);

  // =========================
  // Details Grid (bottom table)
  // =========================
  const dateRange: string[] = useMemo(
    () =>
      scanDetails ? generateDateRange(scanDetails.metrics_window_days) : [],
    [scanDetails]
  );

  const dateRangeLabel = useMemo(() => {
    if (!dateRange.length) return '';
    return dateRange[0] + '–' + dateRange[dateRange.length - 1];
  }, [dateRange]);

  type DetailRow = {
    id: string;
    http_status: number;
    counts: number[]; // aligned to dateRange
    total: number;
  };

  const detailRows: DetailRow[] = useMemo(() => {
    if (!scanDetails) return [];
    return scanDetails.daily_status_counts.map((status) => {
      const countMap: Record<string, number> = Object.fromEntries(
        status.daily_counts.map((d) => [d.date, d.count])
      );
      const counts = dateRange.map((d) => countMap[d] ?? 0);
      const total = counts.reduce((a, b) => a + b, 0);
      return {
        id: String(status.http_status),
        http_status: status.http_status,
        counts,
        total
      };
    });
  }, [scanDetails, dateRange]);

  const detailColumns: GridColDef[] = useMemo(() => {
    const cols: GridColDef[] = [
      {
        field: 'http_status',
        headerName: 'Status Code',
        minWidth: 120,
        flex: 0.6,
        renderCell: (params: GridRenderCellParams<DetailRow>) => (
          <Box
            component="span"
            aria-label={
              'HTTP status code ' +
              params.row.http_status +
              ' for scan ' +
              (scanDetails ? scanDetails.name : '')
            }
          >
            {params.row.http_status}
          </Box>
        )
      },
      {
        field: 'counts',
        headerName: 'Trend',
        minWidth: 220,
        flex: 1.2,
        sortable: false,
        filterable: false,
        disableColumnMenu: true,
        renderCell: (params: GridRenderCellParams<DetailRow>) => {
          const color = getStatusColor(params.row.http_status);
          const ariaText =
            'HTTP ' +
            params.row.http_status +
            ' trend for scan ' +
            (scanDetails ? scanDetails.name : '') +
            ' over ' +
            dateRangeLabel;
          return (
            <Box sx={{ width: '100%' }} aria-label={ariaText}>
              <SparkLineChart
                data={params.row.counts}
                height={40}
                plotType="line"
                showHighlight={false}
                curve="linear"
                color={color}
              />
            </Box>
          );
        }
      },
      {
        field: 'total',
        headerName: 'Total',
        minWidth: 100,
        flex: 0.5,
        align: 'right',
        headerAlign: 'right',
        renderCell: (params: GridRenderCellParams<DetailRow>) => (
          <Box
            component="span"
            aria-label={
              'HTTP Status ' +
              params.row.http_status +
              ' total count ' +
              params.row.total +
              ' for scan ' +
              (scanDetails ? scanDetails.name : '') +
              ' over last ' +
              (scanDetails ? scanDetails.metrics_window_days : '') +
              ' days'
            }
          >
            {params.row.total}
          </Box>
        )
      }
    ];
    return cols;
  }, [dateRangeLabel, scanDetails]);

  // =========================
  // Accessible grouping labels for status categories in header (summary)
  // =========================
  const statusCategoryLabels: Record<number, string> = {
    1: 'Informational',
    2: 'Success',
    3: 'Redirect',
    4: 'Client Error',
    5: 'Server Error'
  };
  const getCategoryCounts = (codes: number[]) => {
    return codes.reduce(
      (acc, code) => {
        const cat = Math.floor(code / 100);
        acc[cat] = (acc[cat] || 0) + 1;
        return acc;
      },
      {} as Record<number, number>
    );
  };
  const categoryCounts = getCategoryCounts(allStatusCodes);

  // Helper to render an extra, visually-hidden description before the grid
  const SummaryHeader: React.FC = () => (
    <Box component="p" sx={visuallyHidden as any}>
      {'Grouped columns: ' +
        Object.entries(categoryCounts)
          .map(function (pair) {
            return (
              (statusCategoryLabels[Number(pair[0])] || 'Other') +
              ' has ' +
              pair[1] +
              ' columns'
            );
          })
          .join('. ')}
    </Box>
  );

  return (
    <Paper
      elevation={0}
      className={cardRoot}
      style={{ padding: '1.25rem 1.25rem' }}
    >
      <div className={cardSmall}>
        <div className={header}>
          <Box
            sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
            aria-label="Scan Metrics heading with information tooltip"
          >
            <Box>
              <InfoLabel
                label="Scan Metrics"
                typographyVariant="h2"
                viewDetails
                tooltipContentJson={scanMetricsTooltip}
                labelStyle={{
                  fontWeight: 600,
                  color: '#07648D',
                  margin: 0
                }}
              />
            </Box>
          </Box>
        </div>
        <div className={body}>
          {scanSummaries?.scans?.length ? (
            <>
              <h3 style={{ margin: 0 }}>
                Scan Result Summary (Last {metricsWindowDays} Days)
              </h3>
              <h4 style={{ fontWeight: 'normal', margin: 0 }}>
                Organization count per scan for each HTTP Status Code
              </h4>

              <SummaryHeader />

              <Box mt={1} aria-label="Scan status summary table">
                <DataGrid
                  rows={summaryRows}
                  columns={summaryColumns}
                  disableRowSelectionOnClick
                  hideFooter
                  onCellKeyDown={(
                    params: GridCellParams,
                    event: React.KeyboardEvent
                  ) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      handleScanClick(String(params.row.id));
                    }
                  }}
                  onCellClick={(params) =>
                    handleScanClick(String(params.row.id))
                  }
                  getRowClassName={() => 'clickable-row'}
                  sx={{
                    '& .clickable-row': { cursor: 'pointer' }
                  }}
                />
              </Box>
            </>
          ) : (
            <h3>No scans available</h3>
          )}

          {selectedScanId && scanDetails && (
            <Box mt={4}>
              <h3 style={{ margin: 0 }}>
                {scanDetails.name} HTTP Status Trends (Last{' '}
                {scanDetails.metrics_window_days} Days)
              </h3>
              <Box
                mt={1}
                ref={detailsRegionRef}
                tabIndex={-1}
                role="region"
                aria-live="polite"
                aria-label={
                  'HTTP status trends table for scan ' + scanDetails.name
                }
              >
                <DataGrid
                  rows={detailRows}
                  columns={detailColumns}
                  getRowId={(row) => row.id}
                  disableRowSelectionOnClick
                  hideFooter
                  sx={{
                    '& .MuiDataGrid-cell:focus-within': {
                      outline: '2px solid #1976d2',
                      outlineOffset: '-2px'
                    }
                  }}
                />
              </Box>
            </Box>
          )}
        </div>
      </div>
    </Paper>
  );
};

export default ScansWidget;
