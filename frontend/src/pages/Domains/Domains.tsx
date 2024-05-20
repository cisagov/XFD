import React, {
  useCallback,
  useState,
  // useMemo,
  // useRef,
  useEffect
} from 'react';
import { useHistory } from 'react-router-dom';
// import { TableInstance } from 'react-table';
import { Query } from 'types';
import { Table, Paginator, Subnav } from 'components';
import { Domain } from 'types';
// import { createColumns } from './columns';
import { useAuthContext } from 'context';
// import classes from './styles.module.scss';
import { useDomainApi } from 'hooks';
import { Box } from '@mui/system';
import { Alert, IconButton, Paper } from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import { differenceInCalendarDays, parseISO } from 'date-fns';

// const PAGE_SIZE = 15;

export const Domains: React.FC = () => {
  const { showAllOrganizations } = useAuthContext();
  // const tableRef = useRef<TableInstance<Domain>>(null);
  // const columns = useMemo(() => createColumns(), []);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [totalResults, setTotalResults] = useState(0);

  const { listDomains, listAllDomains } = useDomainApi(showAllOrganizations);

  // const fetchDomains = useCallback(
  //   async (q: Query<Domain>) => {
  //     try {
  //       const { domains, count } = await listDomains(q);
  //       setDomains(domains);
  //       setTotalResults(count);
  //     } catch (e) {
  //       console.error(e);
  //     }
  //   },
  //   [listDomains]
  // );

  // const fetchDomainsExport = async (): Promise<string> => {
  //   const { sortBy, filters } = tableRef.current?.state ?? {};
  //   try {
  //     const { url } = await listDomains(
  //       {
  //         sort: sortBy ?? [],
  //         page: 1,
  //         pageSize: -1,
  //         filters: filters ?? []
  //       },
  //       true
  //     );
  //     return url!;
  //   } catch (e) {
  //     console.error(e);
  //     return '';
  //   }
  // };

  // const renderPagination = (table: TableInstance<Domain>) => (
  //   <Paginator
  //     table={table}
  //     totalResults={totalResults}
  //     export={{
  //       name: 'domains',
  //       getDataToExport: fetchDomainsExport
  //     }}
  //   />
  // );

  //Code for new table//

  const fetchAllDomains = useCallback(
    async (q: Query<Domain>) => {
      try {
        const { domains, count } = await listAllDomains(q);
        setDomains(domains);
        setTotalResults(count);
      } catch (e) {
        console.error(e);
      }
    },
    [listAllDomains]
  );

  useEffect(() => {
    fetchAllDomains({
      page: 1,
      sort: [],
      filters: []
    });
  }, [fetchAllDomains]);

  console.log(domains);
  console.log(totalResults);

  const testDomains = domains.map((domain) => ({
    id: domain.id,
    organization: domain.organization.name,
    name: domain.name,
    ip: domain.ip,
    ports: domain.services.map((service) => service.port).join(', '),
    service: domain.services.map((service) =>
      service.products.map((p) => p.name).join(', ')
    ),
    vulnerabilities: domain.vulnerabilities.map((vuln) => vuln.cve).join(', '),
    updatedAt: `${differenceInCalendarDays(
      Date.now(),
      parseISO(domain.updatedAt)
    )} days ago`,
    createdAt: `${differenceInCalendarDays(
      Date.now(),
      parseISO(domain.createdAt)
    )} days ago`
  }));

  const history = useHistory();
  const domCols: GridColDef[] = [
    {
      field: 'organization',
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
    <>
      <div>
        <Subnav
          items={[
            { title: 'Search Results', path: '/inventory', exact: true },
            { title: 'All Domains', path: '/inventory/domains' },
            { title: 'All Vulnerabilities', path: '/inventory/vulnerabilities' }
          ]}
        ></Subnav>
        <br></br>
        {/* <Table<Domain>
          renderPagination={renderPagination}
          tableRef={tableRef}
          columns={columns}
          data={domains}
          pageCount={Math.ceil(totalResults / PAGE_SIZE)}
          fetchData={fetchDomains}
          pageSize={PAGE_SIZE}
        /> */}
      </div>
      <div>
        <Box mb={3} mt={3} display="flex" justifyContent="center">
          <Paper elevation={2} sx={{ width: '90%' }}>
            {domains?.length === 0 ? (
              <Alert severity="warning">Unable to load domains.</Alert>
            ) : (
              <DataGrid
                rows={testDomains}
                rowCount={totalResults}
                columns={domCols}
                slots={{ toolbar: CustomToolbar }}
                initialState={{
                  pagination: {
                    paginationModel: {
                      pageSize: 15,
                      page: 0
                    }
                  }
                }}
                pageSizeOptions={[15, 25, 50, 100]}
              />
            )}
          </Paper>
        </Box>
      </div>
    </>
  );
};
