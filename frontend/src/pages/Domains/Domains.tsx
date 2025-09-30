import React, { useCallback, useState, useEffect } from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import { Query } from 'types';
import { DomainSearchApiResponse } from 'types';
import { useAuthContext } from 'context';
import { useDomainApi } from 'hooks';
import { Box, Stack } from '@mui/system';
import {
  Alert,
  Button,
  Divider,
  IconButton,
  Paper,
  Typography
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import FiberManualRecordRounded from '@mui/icons-material/FiberManualRecordRounded';
import {
  DataGrid,
  GridColDef,
  GridRenderCellParams,
  GridSortModel
} from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import CustomNoRowsOverlay from 'components/DataGrid/CustomNoRowsOverlay';
import { differenceInCalendarDays, parseISO } from 'date-fns';
import { FindingsHeader } from 'components/FindingsLibrary/FindingsHeader';
import { extractInitialFilters } from 'utils/vulnerabilitiesTableUtils';

const PAGE_SIZE = 15;

export interface DomainRow {
  id: string;
  organization_name: string;
  name: string;
  ip: string;
  ports_preview: string;
  services_preview: string;
  services_count: number;
  vulnerabilities_count: number;
  updated_at: string;
  created_at: string;
}

export const Domains: React.FC = () => {
  const location = useLocation();
  const state = location.state as
    | { orgName?: string; orgId?: string }
    | undefined;
  const { showAllOrganizations } = useAuthContext();
  const [domains, setDomains] = useState<DomainSearchApiResponse[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const { listDomains } = useDomainApi(
    showAllOrganizations,
    state?.orgId ?? ''
  );
  const history = useHistory();
  const [filters, setFilters] = useState<
    Query<DomainSearchApiResponse>['filters']
  >([]);
  const [loadingError, setLoadingError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasPreloadedFilters, setPreloadedFiltersActive] = useState(false);
  const [sortModel, setSortModel] = useState<GridSortModel>([]);

  useEffect(() => {
    if (state) {
      const extracted = extractInitialFilters(state);
      setFilters(extracted);
      setPreloadedFiltersActive(extracted.length > 0);
    }
  }, [state]);

  const fetchDomains = useCallback(
    async (q: Query<DomainSearchApiResponse>) => {
      try {
        const { domains, count } = await listDomains(q);
        if (domains.length === 0) {
          setDomains([]);
          setTotalResults(0);
          setPaginationModel((prevState) => ({
            ...prevState,
            page: 0,
            pageSize: PAGE_SIZE,
            pageCount: 0,
            filters: q.filters
          }));
          setLoadingError(false);
          return;
        }
        setDomains(domains);
        setTotalResults(count);
        setPaginationModel((prevState) => ({
          ...prevState,
          page: q.page - 1,
          pageSize: q.pageSize ?? PAGE_SIZE,
          pageCount: Math.ceil(count / (q.pageSize ?? PAGE_SIZE)),
          filters: q.filters
        }));
      } catch (e) {
        console.error(e);
        setLoadingError(true);
      } finally {
        setIsLoading(false);
      }
    },
    [listDomains]
  );

  function formatPreview(
    preview: string,
    totalCount: number,
    maxFullCount = 3,
    maxPreviewCount = 2
  ) {
    if (totalCount <= maxFullCount) {
      // Show full preview as-is
      return preview;
    } else {
      // Show first N preview, add (X total)
      const previewItems = preview.split(',').map((item) => item.trim());
      const limitedPreview = previewItems.slice(0, maxPreviewCount).join(', ');
      return `${limitedPreview} (${totalCount} total)`;
    }
  }

  const formatDays = (dateString: string) => {
    const date = parseISO(dateString);
    const days = differenceInCalendarDays(Date.now(), date);
    if (days <= 1) {
      return `${days} day ago`;
    }
    return `${days} days ago`;
  };

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: PAGE_SIZE,
    pageCount: 0,
    filters: filters
  });

  useEffect(() => {
    setIsLoading(true);
    fetchDomains({
      page: 1,
      pageSize: PAGE_SIZE,
      filters,
      order: sortModel[0]?.field,
      sort: sortModel[0]?.sort ?? undefined
    });
  }, [fetchDomains, filters, sortModel]);

  const resetDomains = useCallback(() => {
    history.replace({ ...location, state: null });
    setPreloadedFiltersActive(false);
    setFilters([]);
    setSortModel([]);
    setPaginationModel((prev) => ({
      ...prev,
      page: 0,
      filters: []
    }));
    fetchDomains({
      page: 1,
      pageSize: PAGE_SIZE,
      filters: [],
      order: undefined,
      sort: undefined
    });
  }, [fetchDomains, history, location]);

  const domRows: DomainRow[] = domains.map((domain) => ({
    id: domain.id,
    organization_name: domain.organization.name,
    name: domain.name,
    ip: domain.ip,
    ports_preview: formatPreview(domain.ports_preview, domain.services_count),
    services_preview: formatPreview(
      domain.services_preview,
      domain.services_count
    ),
    services_count: domain.services_count,
    vulnerabilities_count: domain.vulnerabilities_count,
    updated_at: formatDays(domain.updated_at),
    created_at: formatDays(domain.created_at)
  }));

  const domCols: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Domain',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams<DomainRow>) => {
        return (
          <Box
            component="span"
            aria-label={`Domain Name: ${cellValues.row.name}`}
          >
            {cellValues.row.name}
          </Box>
        );
      }
    },
    {
      field: 'organization_name',
      headerName: 'Organization',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderCellParams<DomainRow>) => {
        return (
          <Box
            component="span"
            aria-label={`Organization using Domain ${cellValues.row.name}: ${cellValues.row.organization_name}`}
          >
            {cellValues.row.organization_name}
          </Box>
        );
      }
    },
    {
      field: 'ip',
      headerName: 'IP',
      minWidth: 50,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams<DomainRow>) => {
        return (
          <Box
            component="span"
            aria-label={`IP Address for Domain ${cellValues.row.name}: ${cellValues.row.ip}`}
          >
            {cellValues.row.ip}
          </Box>
        );
      }
    },
    {
      field: 'ports_preview',
      headerName: 'Ports',
      minWidth: 100,
      flex: 1.2,
      renderCell: (cellValues: GridRenderCellParams<DomainRow>) => {
        return (
          <Box
            component="span"
            aria-label={`Ports for Domain ${cellValues.row.name}: ${cellValues.row.ports_preview}`}
          >
            {cellValues.row.ports_preview}
          </Box>
        );
      }
    },
    {
      field: 'services_preview',
      headerName: 'Services',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderCellParams<DomainRow>) => {
        return (
          <Box
            component="span"
            aria-label={`Services for Domain ${cellValues.row.name}: ${cellValues.row.services_preview}`}
          >
            {cellValues.row.services_preview}
          </Box>
        );
      }
    },
    {
      field: 'vulnerabilities_count',
      headerName: 'Vulnerabilities',
      minWidth: 50,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams<DomainRow>) => {
        return (
          <Box
            component="span"
            aria-label={`Vulnerability Count for Domain ${cellValues.row.name}: ${cellValues.row.vulnerabilities_count}`}
          >
            {cellValues.row.vulnerabilities_count}
          </Box>
        );
      }
    },
    {
      field: 'updated_at',
      headerName: 'Updated At',
      minWidth: 50,
      flex: 0.9,
      renderCell: (cellValues: GridRenderCellParams<DomainRow>) => {
        return (
          <Box
            component="span"
            aria-label={`Date Last Updated At for Domain ${cellValues.row.name}: ${cellValues.row.updated_at}`}
          >
            {cellValues.row.updated_at}
          </Box>
        );
      }
    },
    {
      field: 'created_at',
      headerName: 'Created At',
      minWidth: 50,
      flex: 0.9,
      renderCell: (cellValues: GridRenderCellParams<DomainRow>) => {
        return (
          <Box
            component="span"
            aria-label={`Created At Date for Domain ${cellValues.row.name}: ${cellValues.row.created_at}`}
          >
            {cellValues.row.created_at}
          </Box>
        );
      }
    },
    {
      field: 'view',
      headerName: 'Details',
      minWidth: 100,
      flex: 0.3,
      disableExport: true,
      filterable: false,
      sortable: false,
      disableColumnMenu: true,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            aria-label={`View Details for Domain ${cellValues.row.name}`}
            tabIndex={cellValues.tabIndex}
            color="primary"
            onClick={() =>
              history.push('/inventory/domain/' + cellValues.row.id)
            }
          >
            <OpenInNewIcon />
          </IconButton>
        );
      }
    }
  ];

  const noRowsOverlay = (
    <Paper>
      <Alert severity="warning">
        No Results Found. Please adjust your filters.
      </Alert>
    </Paper>
  );

  return (
    <Box
      display="flex"
      flexDirection="column"
      minHeight="100vh"
      maxWidth="1152px"
      width="100%"
      margin="auto"
    >
      <FindingsHeader />
      {!isLoading && !loadingError && state && hasPreloadedFilters && (
        <Box sx={{ width: '100%', mb: 1 }}>
          <Stack direction="row" alignItems="center">
            <FiberManualRecordRounded sx={{ color: 'primary.main' }} />
            <Typography variant="body1" color="neutrals.main">
              &nbsp;Filters Applied:
            </Typography>
            {state.orgName ? (
              <Typography variant="body1" color="neutrals.main" ml={1}>
                <b>Organization</b> - {state.orgName}
              </Typography>
            ) : (
              ''
            )}
            <Divider
              orientation="vertical"
              flexItem
              variant="middle"
              sx={{
                height: 24,
                alignSelf: 'center',
                borderColor: 'neutrals.light',
                ml: 2
              }}
            />
            <Button
              variant="text"
              onClick={resetDomains}
              sx={{
                color: 'primary.dark',
                fontSize: '14px',
                fontWeight: 'bold',
                lineHeight: '20px',
                letterSpacing: '0.1em',
                ml: 1
              }}
            >
              Reset
            </Button>
          </Stack>
        </Box>
      )}
      <Box mb={3} display="flex" justifyContent="center">
        {isLoading ? (
          <Paper elevation={2}>
            <Alert severity="info">Loading Domains..</Alert>
          </Paper>
        ) : isLoading === false && loadingError === true ? (
          <Stack direction="row" spacing={2}>
            <Paper elevation={2}>
              <Alert severity="warning">Error Loading Domains!</Alert>
            </Paper>
            <Button
              onClick={() => fetchDomains}
              variant="contained"
              color="primary"
              sx={{ width: 'fit-content' }}
            >
              Retry
            </Button>
          </Stack>
        ) : isLoading === false && loadingError === false ? (
          <Paper
            elevation={2}
            sx={{ width: '100%', minHeight: 500 }}
            aria-label="Domains Table"
          >
            <DataGrid
              rows={domRows}
              rowCount={totalResults}
              columns={domCols}
              sortingMode="server"
              sortModel={sortModel}
              onSortModelChange={(model) => {
                setSortModel(model);
              }}
              slots={{
                toolbar: CustomToolbar,
                noRowsOverlay: CustomNoRowsOverlay
              }}
              slotProps={{
                noRowsOverlay: { children: noRowsOverlay },
                toolbar: { exportTitle: 'Domains' } as any,
                basePopper: {
                  placement: 'bottom-start'
                }
              }}
              paginationMode="server"
              paginationModel={paginationModel}
              onPaginationModelChange={(model) => {
                fetchDomains({
                  page: model.page + 1,
                  pageSize: model.pageSize,
                  filters: filters,
                  order: sortModel[0]?.field,
                  sort: sortModel[0]?.sort ?? undefined
                });
              }}
              pageSizeOptions={[15, 30, 50, 100]}
              disableRowSelectionOnClick
              showToolbar
            />
          </Paper>
        ) : null}
      </Box>
    </Box>
  );
};
