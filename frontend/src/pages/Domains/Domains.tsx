import React, { useCallback, useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
import { Query } from 'types';
import { Subnav } from 'components';
import { Domain } from 'types';
import { useAuthContext } from 'context';
import { useDomainApi } from 'hooks';
import { Box, Stack } from '@mui/system';
import { Alert, Button, IconButton, Paper } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import { differenceInCalendarDays, parseISO } from 'date-fns';

const PAGE_SIZE = 15;

export interface DomainRow {
  id: string;
  organizationName: string;
  name: string;
  ip: string;
  ports: string[];
  service: string[];
  vulnerabilities: (string | null)[];
  updatedAt: string;
  createdAt: string;
}

export const Domains: React.FC = () => {
  const { showAllOrganizations } = useAuthContext();
  const [domains, setDomains] = useState<Domain[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const { listDomains } = useDomainApi(showAllOrganizations);
  const history = useHistory();
  const [filters, setFilters] = useState<Query<Domain>['filters']>([]);
  const [loadingError, setLoadingError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [filterModel, setFilterModel] = useState({
    items: filters.map((filter) => ({
      id: filter.id,
      field: filter.field,
      value: filter.value,
      operator: filter.operator
    }))
  });
  // TO-DO
  // Implement regional rollup on domains view to allow for proper domain drilldown from dashboard
  const fetchDomains = useCallback(
    async (q: Query<Domain>) => {
      try {
        const { domains, count } = await listDomains(q);
        if (domains.length === 0) return;
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
      filters: []
    });
  }, [fetchDomains]);

  const domRows: DomainRow[] = domains.map((domain) => ({
    id: domain.id,
    organizationName: domain.organization.name,
    name: domain.name,
    ip: domain.ip,
    ports: [domain.services.map((service) => service.port).join(', ')],
    service: domain.services.map((service) =>
      service.products.map((p) => p.name).join(', ')
    ),
    vulnerabilities: domain.vulnerabilities.map((vuln) => vuln.cve),
    updatedAt: `${differenceInCalendarDays(
      Date.now(),
      parseISO(domain.updatedAt)
    )} days ago`,
    createdAt: `${differenceInCalendarDays(
      Date.now(),
      parseISO(domain.createdAt)
    )} days ago`
  }));

  const domCols: GridColDef[] = [
    {
      field: 'organizationName',
      headerName: 'Organization',
      minWidth: 100,
      flex: 1
    },
    { field: 'name', headerName: 'Domain', minWidth: 100, flex: 2 },
    { field: 'ip', headerName: 'IP', minWidth: 50, flex: 1 },
    { field: 'ports', headerName: 'Ports', minWidth: 100, flex: 1 },
    { field: 'service', headerName: 'Services', minWidth: 100, flex: 2 },
    {
      field: 'vulnerabilities',
      headerName: 'Vulnerabilities',
      minWidth: 100,
      flex: 2
    },
    { field: 'updatedAt', headerName: 'Updated At', minWidth: 50, flex: 1 },
    { field: 'createdAt', headerName: 'Created At', minWidth: 50, flex: 1 },

    {
      field: 'view',
      headerName: 'Details',
      minWidth: 100,
      flex: 0.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            aria-label={`View details for ${cellValues.row.name}`}
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

  return (
    <Box>
      <Subnav
        items={[
          { title: 'Search Results', path: '/inventory', exact: true },
          { title: 'All Domains', path: '/inventory/domains' },
          { title: 'All Vulnerabilities', path: '/inventory/vulnerabilities' }
        ]}
      ></Subnav>
      <Box mb={3} mt={5} display="flex" justifyContent="center">
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
          <Paper elevation={2} sx={{ width: '90%', minHeight: '200px' }}>
            <DataGrid
              rows={domRows}
              rowCount={totalResults}
              columns={domCols}
              slots={{ toolbar: CustomToolbar }}
              paginationMode="server"
              paginationModel={paginationModel}
              onPaginationModelChange={(model) => {
                fetchDomains({
                  page: model.page + 1,
                  pageSize: model.pageSize,
                  filters: paginationModel.filters
                });
              }}
              filterMode="server"
              filterModel={filterModel}
              onFilterModelChange={(model) => {
                const filters = model.items.map((item) => ({
                  id: item.field,
                  field: item.field,
                  value: item.value,
                  operator: item.operator
                }));
                setFilters(filters);
                setFilterModel((prevFilterModel) => ({
                  ...prevFilterModel,
                  items: filters
                }));
                fetchDomains({
                  page: paginationModel.page + 1,
                  pageSize: paginationModel.pageSize,
                  filters: filters
                });
              }}
              pageSizeOptions={[15, 30, 50, 100]}
            />
          </Paper>
        ) : null}
      </Box>
    </Box>
  );
};
