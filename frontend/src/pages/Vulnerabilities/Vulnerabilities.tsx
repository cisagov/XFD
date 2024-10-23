import React, { useState, useCallback, useEffect } from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import { Query } from 'types';
import { useAuthContext } from 'context';
import { Vulnerability as VulnerabilityType } from 'types';
import { Subnav } from 'components';
import {
  Alert,
  Box,
  Button,
  IconButton,
  MenuItem,
  Menu,
  Paper,
  Stack,
  Typography
} from '@mui/material';
import {
  DataGrid,
  GridColDef,
  GridFilterItem,
  GridRenderCellParams
} from '@mui/x-data-grid';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { getSeverityColor } from 'pages/Risk/utils';
import { differenceInCalendarDays, parseISO } from 'date-fns';
import { truncateString } from 'utils/dataTransformUtils';
import { ORGANIZATION_EXCLUSIONS } from 'hooks/useUserTypeFilters';

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

export interface LooseVulnerabilityRow {
  id: string;
  title: string;
  severity: string;
  kev: string;
  domain: string | undefined;
  domainId: string | undefined;
  product: string;
  createdAt: string;
  state: string;
}

type Nullable<T> = {
  [P in keyof T]: T[P] | null;
};

type VulnerabilityRow = Nullable<LooseVulnerabilityRow>;

type Vulnerability = Nullable<VulnerabilityType>;

interface LocationState {
  domain: any;
  severity: string;
  title: string;
}

export const Vulnerabilities: React.FC<{ groupBy?: string }> = ({
  groupBy = undefined
}: {
  children?: React.ReactNode;
  groupBy?: string;
}) => {
  const { currentOrganization, apiPost, apiPut } = useAuthContext();
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [loadingError, setLoadingError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // TO-DO
  // Implement regional rollup for vulnerabilities view to allow for proper vunl drilldown from dashboard
  const updateVulnerability = useCallback(
    async (index: number, body: { [key: string]: string }) => {
      try {
        const updatedVulns = await apiPut<Vulnerability>(
          '/vulnerabilities/' + vulnerabilities[index].id,
          {
            body: body
          }
        );
        setVulnerabilities((prevState) =>
          prevState.map((orgVulns, targetIndex) =>
            targetIndex === index ? updatedVulns : orgVulns
          )
        );
      } catch (e) {
        console.error(e);
      }
    },
    [setVulnerabilities, apiPut, vulnerabilities]
  );

  const vulnerabilitiesSearch = useCallback(
    async ({
      filters,
      page,
      pageSize = PAGE_SIZE,
      doExport = false,
      groupBy = undefined
    }: {
      filters: GridFilterItem[];
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
              [next.field]: next.value
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
        let userOrgIsExcluded = false;
        ORGANIZATION_EXCLUSIONS.forEach((exc) => {
          if (currentOrganization?.name.toLowerCase().includes(exc)) {
            userOrgIsExcluded = true;
          }
        });
        if (currentOrganization && !userOrgIsExcluded) {
          tableFilters['organization'] = currentOrganization.id;
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
              filters: tableFilters,
              pageSize,
              groupBy
            }
          }
        );
      } catch (e) {
        console.error(e);
        setLoadingError(true);
        return;
      }
    },
    [apiPost, currentOrganization]
  );

  const fetchVulnerabilities = useCallback(
    async (query: Query<Vulnerability>) => {
      try {
        const resp = await vulnerabilitiesSearch({
          filters: query.filters,
          page: query.page,
          pageSize: query.pageSize ?? PAGE_SIZE,
          groupBy
        });
        if (!resp) return;
        const { result, count } = resp;
        if (result.length === 0) return;
        setVulnerabilities(result);
        setTotalResults(count);
        setPaginationModel((prevState) => ({
          ...prevState,
          page: query.page - 1,
          pageSize: query.pageSize ?? PAGE_SIZE,
          pageCount: Math.ceil(count / (query.pageSize ?? PAGE_SIZE)),
          filters: query.filters
        }));
      } catch (e) {
        console.error(e);
        setLoadingError(true);
      } finally {
        setIsLoading(false);
      }
    },
    [vulnerabilitiesSearch, groupBy]
  );

  const history = useHistory();
  const location = useLocation();
  const state = location.state as LocationState;
  const [initialFilters, setInitialFilters] = useState<GridFilterItem[]>(
    state?.title
      ? [
          {
            field: 'title',
            value: state.title,
            operator: 'contains'
          }
        ]
      : state?.domain
      ? [
          {
            field: 'domain',
            value: state.domain,
            operator: 'contains'
          }
        ]
      : state?.severity
      ? [
          {
            field: 'severity',
            value: state.severity,
            operator: 'contains'
          }
        ]
      : []
  );
  const [filters, setFilters] = useState(initialFilters);

  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: PAGE_SIZE,
    pageCount: 0,
    filters: filters
  });

  const [filterModel, setFilterModel] = useState({
    items: filters.map((filter) => ({
      id: filter.id,
      field: filter.field,
      value: filter.value,
      operator: filter.operator
    }))
  });
  // Row scoped menu state management for vulnerability status updates
  interface MenuState {
    [key: string]: {
      anchorEl: HTMLElement | null;
      open: boolean;
    };
  }

  const [menuState, setMenuState] = useState<MenuState>({});

  const handleMenuClick = (
    event: React.MouseEvent<HTMLButtonElement>,
    rowId: any
  ) => {
    setMenuState((prev) => ({
      ...prev,
      [rowId]: {
        anchorEl: event.currentTarget,
        open: true
      }
    }));
  };

  const handleClose = (rowId: any) => {
    setMenuState((prev) => ({
      ...prev,
      [rowId]: {
        ...prev[rowId],
        open: false
      }
    }));
  };

  const resetVulnerabilities = useCallback(() => {
    setInitialFilters([]);
    fetchVulnerabilities({
      page: 1,
      pageSize: PAGE_SIZE,
      filters: []
    });
  }, [fetchVulnerabilities]);

  useEffect(() => {
    setIsLoading(true);
    fetchVulnerabilities({
      page: 1,
      pageSize: PAGE_SIZE,
      filters: initialFilters
    });
  }, [fetchVulnerabilities, initialFilters]);

  const vulRows: VulnerabilityRow[] = vulnerabilities.map((vuln) => ({
    id: vuln.id,
    title: vuln.title,
    severity: vuln.severity ?? 'N/A',
    kev: vuln.isKev ? 'Yes' : 'No',
    domain: vuln?.domain?.name,
    domainId: vuln?.domain?.id,
    product: vuln.cpe
      ? vuln.cpe
      : vuln.service &&
        vuln.service.products &&
        vuln.service.products.length > 0 &&
        vuln.service.products[0].cpe
      ? vuln.service.products[0].cpe || 'N/A'
      : 'N/A',
    createdAt: vuln?.createdAt
      ? `${differenceInCalendarDays(
          Date.now(),
          parseISO(vuln?.createdAt)
        )} days`
      : '',
    state: vuln.state + (vuln.substate ? ` (${vuln.substate})` : '')
  }));

  const vulCols: GridColDef[] = [
    {
      field: 'title',
      headerName: 'Vulnerability',
      minWidth: 100,
      flex: 1.2,
      renderCell: (cellValues: GridRenderCellParams) => {
        if (cellValues.row.title.startsWith('CVE')) {
          return (
            <Button
              aria-label={`View NIST entry for ${cellValues.row.title}`}
              tabIndex={cellValues.tabIndex}
              color="primary"
              style={{ textDecorationLine: 'underline' }}
              endIcon={<OpenInNewIcon />}
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
        return (
          <Typography pl={1}>{truncateString(cellValues.row.title)}</Typography>
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
      minWidth: 50,
      flex: 0.3
    },
    {
      field: 'domain',
      headerName: 'Domain',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Button
            aria-label={`View details for ${cellValues.row.domain}`}
            tabIndex={cellValues.tabIndex}
            color="primary"
            style={{ textDecorationLine: 'underline' }}
            sx={{ justifyContent: 'flex-start' }}
            endIcon={<OpenInNewIcon />}
            onClick={() =>
              history.push('/inventory/domain/' + cellValues.row.domainId)
            }
          >
            {cellValues.row.domain}
          </Button>
        );
      }
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
        const handleUpdate = (id: string, substate: string) => {
          const index = vulnerabilities.findIndex((v) => v.id === id);
          updateVulnerability(index, {
            substate: substate
          });
        };

        return (
          <div>
            <Button
              id={`basic-button-${cellValues.row.id}`}
              style={{ textDecorationLine: 'underline' }}
              aria-controls={
                menuState[cellValues.row.id]?.open
                  ? `basic-menu-${cellValues.row.id}`
                  : undefined
              }
              aria-haspopup="true"
              aria-expanded={
                menuState[cellValues.row.id]?.open ? 'true' : undefined
              }
              tabIndex={cellValues.tabIndex}
              endIcon={<ExpandMoreIcon />}
              onClick={(event) => handleMenuClick(event, cellValues.row.id)}
            >
              {cellValues.row.state}
            </Button>
            <Menu
              id={`basic-menu-${cellValues.row.id}`}
              anchorEl={menuState[cellValues.row.id]?.anchorEl}
              open={menuState[cellValues.row.id]?.open}
              onClose={() => handleClose(cellValues.row.id)}
              MenuListProps={{
                'aria-labelledby': `basic-button-${cellValues.row.id}`
              }}
            >
              {Object.keys(stateMap).map((substate) => (
                <MenuItem
                  key={`${cellValues.row.id}-${substate}`}
                  id={`menu-item-${cellValues.row.id}-${substate}`}
                  onClick={() => {
                    handleUpdate(cellValues.row.id, substate);
                    handleClose(cellValues.row.id);
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
            aria-label={`View details for ${cellValues.row.title}`}
            tabIndex={cellValues.tabIndex}
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
            <Alert severity="info">Loading Vulnerabilities..</Alert>
          </Paper>
        ) : isLoading === false && loadingError === true ? (
          <Stack direction="row" spacing={2}>
            <Paper elevation={2}>
              <Alert severity="warning">Error Loading Vulnerabilities!</Alert>
            </Paper>
            <Button
              onClick={resetVulnerabilities}
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
              rows={vulRows}
              rowCount={totalResults}
              columns={vulCols}
              slots={{ toolbar: CustomToolbar }}
              paginationMode="server"
              paginationModel={paginationModel}
              onPaginationModelChange={(model) => {
                fetchVulnerabilities({
                  page: model.page + 1,
                  pageSize: model.pageSize,
                  filters: paginationModel.filters
                });
              }}
              filterMode="server"
              filterModel={filterModel}
              onFilterModelChange={(model) => {
                const filters = model.items.map((item) => ({
                  id: item.id,
                  field: item.field,
                  value: item.value,
                  operator: item.operator
                }));
                setFilters(filters);
                setFilterModel((prevFilterModel) => ({
                  ...prevFilterModel,
                  items: filters
                }));
                fetchVulnerabilities({
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

export default Vulnerabilities;
