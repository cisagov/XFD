import React, {
  useState,
  useCallback,
  useRef,
  useMemo,
  useEffect
} from 'react';
import { useHistory } from 'react-router-dom';
import { classesVulns, Root } from './vulnerabilitiesStyle';
import { TableInstance, Filters, SortingRule } from 'react-table';
import { Query } from 'types';
import { useAuthContext } from 'context';
// import { Table, Paginator } from 'components';
import { Vulnerability } from 'types';
// import classes from './styles.module.scss';
import { Subnav } from 'components';
// import { parse } from 'query-string';
import { createColumns, createGroupedColumns } from './columns';
import {
  Paper,
  Alert,
  Button,
  IconButton,
  MenuItem,
  // Select,
  Menu
  // FormControl,
  // InputLabel
} from '@mui/material';
import { Box, Stack } from '@mui/system';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { getSeverityColor } from 'pages/Risk/utils';
// import { he } from 'date-fns/locale';
import { differenceInCalendarDays, parseISO, sub } from 'date-fns';
// import { Form } from '@trussworks/react-uswds';

export interface ApiResponse {
  result: Vulnerability[];
  count: number;
  url?: string;
}

const PAGE_SIZE = 15;

export const stateMap: { [key: string]: string } = {
  unconfirmed: 'Unconfirmed',
  exploitable: 'Exploitable',
  'false-positive': 'False Positive',
  'accepted-risk': 'Accepted Risk',
  remediated: 'Remediated'
};

export const Vulnerabilities: React.FC<{ groupBy?: string }> = ({
  groupBy = undefined
}: {
  children?: React.ReactNode;
  groupBy?: string;
}) => {
  const { currentOrganization, apiPost, apiPut, showAllOrganizations } =
    useAuthContext();
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const tableRef = useRef<TableInstance<Vulnerability>>(null);

  const [noResults, setNoResults] = useState(false);

  const updateVulnerability = useCallback(
    async (index: number, body: { [key: string]: string }) => {
      try {
        const res = await apiPut<Vulnerability>(
          '/vulnerabilities/' + vulnerabilities[index].id,
          {
            body: body
          }
        );
        const vulnCopy = [...vulnerabilities];
        vulnCopy[index].state = res.state;
        vulnCopy[index].substate = res.substate;
        vulnCopy[index].actions = res.actions;
        setVulnerabilities(vulnCopy);
      } catch (e) {
        console.error(e);
      }
    },
    [setVulnerabilities, apiPut, vulnerabilities]
  );
  const columns = useMemo(
    () => createColumns(updateVulnerability),
    [updateVulnerability]
  );
  const groupedColumns = useMemo(() => createGroupedColumns(), []);

  const vulnerabilitiesSearch = useCallback(
    async ({
      filters,
      sort,
      page,
      pageSize = PAGE_SIZE,
      doExport = false,
      groupBy = undefined
    }: {
      filters: Filters<Vulnerability>;
      sort: SortingRule<Vulnerability>[];
      page: number;
      pageSize?: number;
      doExport?: boolean;
      groupBy?: string;
    }): Promise<ApiResponse | undefined> => {
      try {
        const tableFilters: {
          [key: string]: string | boolean | undefined;
        } = filters
          .filter((f) => Boolean(f.value))
          .reduce(
            (accum, next) => ({
              ...accum,
              [next.id]: next.value
            }),
            {}
          );
        // If not open or closed, substitute for appropriate substate
        if (
          tableFilters['state'] &&
          !['open', 'closed'].includes(tableFilters['state'] as string)
        ) {
          const substate = (tableFilters['state'] as string)
            .match(/\((.*)\)/)
            ?.pop();
          if (substate)
            tableFilters['substate'] = substate.toLowerCase().replace(' ', '-');
          delete tableFilters['state'];
        }
        if (!showAllOrganizations && currentOrganization) {
          if ('rootDomains' in currentOrganization)
            tableFilters['organization'] = currentOrganization.id;
          else tableFilters['tag'] = currentOrganization.id;
        }
        if (tableFilters['isKev']) {
          // Convert string to boolean filter.
          tableFilters['isKev'] = tableFilters['isKev'] === 'true';
        }
        return await apiPost<ApiResponse>(
          doExport ? '/vulnerabilities/export' : '/vulnerabilities/search',
          {
            body: {
              page,
              sort: sort[0]?.id ?? 'createdAt',
              order: sort[0]?.desc ? 'DESC' : 'ASC',
              filters: tableFilters,
              pageSize,
              groupBy
            }
          }
        );
      } catch (e) {
        console.error(e);
        return;
      }
    },
    [apiPost, currentOrganization, showAllOrganizations]
  );

  const fetchVulnerabilities = useCallback(
    async (query: Query<Vulnerability>) => {
      try {
        const resp = await vulnerabilitiesSearch({
          filters: query.filters,
          sort: query.sort,
          page: query.page,
          pageSize: query.pageSize ?? PAGE_SIZE,
          groupBy
        });
        if (!resp) return;
        const { result, count } = resp;
        if (result.length === 0) return;
        setVulnerabilities(result);
        setTotalResults(count);
        setNoResults(count === 0);
        setPaginationModel((prevState) => ({
          ...prevState,
          page: query.page - 1,
          pageSize: query.pageSize ?? PAGE_SIZE,
          pageCount: Math.ceil(count / (query.pageSize ?? PAGE_SIZE))
        }));
      } catch (e) {
        console.error(e);
      }
    },
    [vulnerabilitiesSearch, groupBy]
  );

  console.log('vulnerabilities', vulnerabilities);
  // const fetchVulnerabilitiesExport = async (): Promise<string> => {
  //   const { sortBy, filters } = tableRef.current?.state ?? {};
  //   const { url } = (await vulnerabilitiesSearch({
  //     filters: filters!,
  //     sort: sortBy!,
  //     page: 1,
  //     pageSize: -1,
  //     doExport: true
  //   })) as ApiResponse;
  //   return url!;
  // };

  // const renderPagination = (table: TableInstance<Vulnerability>) => (
  //   <Paginator
  //     table={table}
  //     totalResults={totalResults}
  //     export={{
  //       name: 'vulnerabilities',
  //       getDataToExport: fetchVulnerabilitiesExport
  //     }}
  //   />
  // );

  // const initialFilterBy: Filters<Vulnerability> = [];
  // let initialSortBy: SortingRule<Vulnerability>[] = [];
  // const params = parse(window.location.search);
  // if (!('state' in params)) params['state'] = 'open';
  // for (const param of Object.keys(params)) {
  //   if (param === 'sort') {
  //     initialSortBy = [
  //       {
  //         id: params[param] as string,
  //         desc: 'desc' in params ? params['desc'] === 'true' : true
  //       }
  //     ];
  //   } else if (param !== 'desc') {
  //     initialFilterBy.push({
  //       id: param,
  //       value: params[param] as string
  //     });
  //   }
  // }

  //Code for new table//

  const history = useHistory();

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: PAGE_SIZE,
    pageCount: 0,
    sort: [],
    filters: []
  });

  const resetVulnerabilities = useCallback(() => {
    fetchVulnerabilities({
      page: 1,
      pageSize: PAGE_SIZE,
      sort: [],
      filters: []
    });
  }, [fetchVulnerabilities]);

  useEffect(() => {
    fetchVulnerabilities({
      page: 1,
      pageSize: PAGE_SIZE,
      sort: [],
      filters: []
    });
  }, [fetchVulnerabilities]);

  const testVulnerabilities = vulnerabilities.map((vuln) => ({
    id: vuln.id,
    title: vuln.title,
    severity: vuln.severity,
    kev: vuln.isKev ? 'Yes' : 'No',
    domain: vuln.domain.name,
    product: vuln.cpe,
    createdAt: `${differenceInCalendarDays(
      Date.now(),
      parseISO(vuln.createdAt)
    )} days`,
    state: vuln.state + (vuln.substate ? ` (${vuln.substate})` : '')
  }));

  const vulCols: GridColDef[] = [
    {
      field: 'title',
      headerName: 'Vulnerability',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Button
            color="primary"
            style={{ textDecorationLine: 'underline' }}
            onClick={() =>
              window.open(
                'https://nvd.nist.gov/vuln/detail/' + cellValues.row.title
              )
            }
          >
            {cellValues.row.title}
          </Button>
        );
      }
    },
    {
      field: 'severity',
      headerName: 'Severity',
      minWidth: 100,
      flex: 0.5,
      sortComparator: (v1, v2, cellParams1, cellParams2) => {
        const severityLevels: Record<string, number> = {
          Low: 1,
          Medium: 2,
          High: 3,
          Critical: 4
        };
        return (
          severityLevels[cellParams1.value] - severityLevels[cellParams2.value]
        );
      },
      renderCell: (cellValues: GridRenderCellParams) => {
        const severityLevels: Record<string, number> = {
          Low: 1,
          Medium: 2,
          High: 3,
          Critical: 4
        };
        return (
          <Stack>
            <div>{cellValues.row.severity}</div>
            <div style={{ display: 'none' }}>
              ({severityLevels[cellValues.row.severity]})
            </div>
            <Box
              style={{
                height: '.5em',
                width: '5em',
                backgroundColor: getSeverityColor({
                  id: cellValues.row.severity ?? ''
                })
              }}
            ></Box>
          </Stack>
        );
      }
    },
    {
      field: 'kev',
      headerName: 'KEV',
      minWidth: 75,
      flex: 0.5
    },
    {
      field: 'domain',
      headerName: 'Domain',
      minWidth: 100,
      flex: 1
    },
    {
      field: 'product',
      headerName: 'Product',
      minWidth: 100,
      flex: 1
    },
    {
      field: 'createdAt',
      headerName: 'Days Open',
      minWidth: 100,
      flex: 0.5
    },
    {
      field: 'state',
      headerName: 'Status',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
        const open = Boolean(anchorEl);
        const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
          setAnchorEl(event.currentTarget);
        };
        const handleClose = () => {
          setAnchorEl(null);
        };
        const handleUpdate = (substate: string) => {
          const index = vulnerabilities.findIndex(
            (vuln) => vuln.id === cellValues.row.id
          );
          updateVulnerability(index, {
            substate: substate
          });
        };

        return (
          <div>
            <Button
              id="basic-button"
              aria-controls={open ? 'basic-menu' : undefined}
              aria-haspopup="true"
              aria-expanded={open ? 'true' : undefined}
              onClick={handleClick}
            >
              {cellValues.row.state}
            </Button>
            <Menu
              id="basic-menu"
              anchorEl={anchorEl}
              open={open}
              onClose={handleClose}
              MenuListProps={{
                'aria-labelledby': 'basic-button'
              }}
            >
              {Object.keys(stateMap).map((substate) => (
                <MenuItem
                  key={substate}
                  onClick={() => {
                    handleUpdate(substate);
                    handleClose();
                  }}
                >
                  {substate === 'unconfirmed' || substate === 'exploitable'
                    ? 'Open'
                    : 'Closed'}
                  {` (${substate})`}
                </MenuItem>
              ))}
            </Menu>
          </div>
        );
      }
    },
    {
      field: 'viewDetails',
      headerName: 'Details',
      minWidth: 75,
      flex: 0.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <IconButton
            color="primary"
            onClick={() =>
              history.push('/inventory/vulnerability/' + cellValues.row.id)
            }
          >
            <OpenInNewIcon />
          </IconButton>
        );
      }
    }
  ];

  return (
    <Root>
      <div className={classesVulns.contentWrapper}>
        <Subnav
          items={[
            { title: 'Search Results', path: '/inventory', exact: true },
            { title: 'All Domains', path: '/inventory/domains' },
            { title: 'All Vulnerabilities', path: '/inventory/vulnerabilities' }
          ]}
        ></Subnav>
        <br></br>
        {/* <div className={classes.root}>
          <Table<Vulnerability>
            renderPagination={renderPagination}
            columns={groupBy ? groupedColumns : columns}
            data={vulnerabilities}
            pageCount={Math.ceil(totalResults / PAGE_SIZE)}
            fetchData={fetchVulnerabilities}
            tableRef={tableRef}
            initialFilterBy={initialFilterBy}
            initialSortBy={initialSortBy}
            noResults={noResults}
            pageSize={PAGE_SIZE}
            noResultsMessage={
              "We don't see any vulnerabilities that match your criteria."
            }
          />
        </div> */}
        <Box mb={3} mt={3} display="flex" justifyContent="center">
          {vulnerabilities?.length === 0 ? (
            <Stack spacing={2}>
              <Paper elevation={2}>
                <Alert severity="warning">
                  {' '}
                  Unable to load vulnerabilities.
                </Alert>
              </Paper>
              <Stack direction="row" spacing={2} justifyContent="end">
                <Button
                  onClick={resetVulnerabilities}
                  variant="contained"
                  color="primary"
                  sx={{ width: 'fit-content' }}
                >
                  Retry
                </Button>
              </Stack>
            </Stack>
          ) : (
            <Paper elevation={2} sx={{ width: '90%' }}>
              <DataGrid
                rows={testVulnerabilities}
                rowCount={totalResults}
                columns={vulCols}
                slots={{ toolbar: CustomToolbar }}
                paginationMode="server"
                paginationModel={paginationModel}
                onPaginationModelChange={(model) => {
                  fetchVulnerabilities({
                    page: model.page + 1,
                    pageSize: model.pageSize,
                    sort: paginationModel.sort,
                    filters: paginationModel.filters
                  });
                }}
                filterMode="server"
                onFilterModelChange={(model) => {
                  fetchVulnerabilities({
                    page: 1,
                    pageSize: paginationModel.pageSize,
                    sort: paginationModel.sort,
                    filters: model.items.map((item) => ({
                      id: item.field,
                      value: item.value
                    }))
                  });
                }}
                pageSizeOptions={[15, 30, 50, 100]}
              />
            </Paper>
          )}
        </Box>
      </div>
    </Root>
  );
};

export default Vulnerabilities;
