import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';

// Material-UI Components
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutline';

// DataGrid Components
import { DataGrid, GridFilterModel, GridSortModel } from '@mui/x-data-grid';

// Types
import { Organization } from 'types';

// Context
import { useAuthContext } from 'context';

// Components
import { OrganizationForm } from './OrganizationForm';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import CustomPagination from 'components/DataGrid/CustomPagination';
import InfoDialog from 'components/Dialog/InfoDialog';
import { useOrgsColumns } from './useOrgsColumns';

// Utils
import { logger } from '@/utils/logger';

// Constants
import { ENDPOINTS } from '@/constants/endpoints';

type OrgsApiResponse = {
  result: Organization[];
  count: number;
  url?: string;
};

export const Organizations: React.FC = () => {
  const { apiPost, setFeedbackMessage } = useAuthContext();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [rowCount, setRowCount] = useState(0);
  const [loadingError, setLoadingError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [chosenTags, setChosenTags] = useState<string[]>([]);
  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: 15
  });
  const [filterModel, setFilterModel] = useState<GridFilterModel>({
    items: []
  });
  const [debouncedFilterModel, setDebouncedFilterModel] =
    useState<GridFilterModel>(filterModel);
  const [sortModel, setSortModel] = useState<GridSortModel>([]);
  const reqIdRef = useRef(0);

  useEffect(() => {
    const h = setTimeout(() => setDebouncedFilterModel(filterModel), 300);
    return () => clearTimeout(h);
  }, [filterModel]);

  const buildFilters = useCallback((model: GridFilterModel) => {
    const filters: Record<string, any> = {};
    model.items.forEach((i) => {
      if (!i.value) return;
      if (i.field === 'name') {
        const v = String(i.value).trim();
        if (v.length >= 2) filters.name = v; // gate short inputs
      }
      if (i.field === 'state') filters.state = String(i.value).trim();
      if (i.field === 'region_id') filters.region_id = String(i.value).trim();
      if (i.field === 'acronym') filters.acronym = String(i.value).trim();
    });
    return filters;
  }, []);

  const requestBody = useMemo(() => {
    const firstSort = sortModel[0];
    return {
      page: paginationModel.page + 1,
      pageSize: paginationModel.pageSize,
      sort: firstSort?.field || undefined,
      order: firstSort?.sort || undefined,
      filters: buildFilters(debouncedFilterModel)
    };
  }, [paginationModel, debouncedFilterModel, sortModel, buildFilters]);

  const fetchOrganizations = useCallback(async () => {
    const myId = ++reqIdRef.current;
    setIsLoading(true);
    setLoadingError(false);
    try {
      const data = await apiPost<OrgsApiResponse>(
        ENDPOINTS.ORGANIZATIONS_SEARCH,
        {
          body: requestBody
        }
      );
      if (myId !== reqIdRef.current) return; // ignore stale responses
      setOrganizations(data.result);
      setRowCount(data.count);
    } catch (e) {
      if (myId === reqIdRef.current) {
        logger.error('Organizations.fetchOrganizations failed:', { error: e });
        setLoadingError(true);
      }
    } finally {
      if (myId === reqIdRef.current) setIsLoading(false);
    }
  }, [apiPost, requestBody]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  const orgCols = useOrgsColumns();

  const onSubmit = async (body: Object) => {
    try {
      const org = await apiPost<Organization>(ENDPOINTS.ORGANIZATIONS, {
        body
      });
      setOrganizations((prev) => [...prev, org]);
      setInfoDialogOpen(true);
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422
            ? 'Error when submitting organization entry.'
            : (e.message ?? e.toString()),
        type: 'error'
      });
      setChosenTags([]);
      logger.error('Organizations.handleSubmit failed:', { error: e });
    }
  };

  return (
    <Box
      sx={{
        maxWidth: '1152px',
        width: '100%',
        margin: 'auto',
        px: { xs: 0, sm: 0.5, md: 1, lg: 1, xl: 1 },
        pb: 3,
        minHeight: '100vh'
      }}
    >
      <Typography
        fontSize={34}
        fontWeight="medium"
        letterSpacing={0}
        my={3}
        variant="h1"
      >
        Organizations
      </Typography>

      {loadingError && (
        <Box mb={2}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Alert severity="warning" sx={{ flex: 1 }}>
              Error Loading Organizations!
            </Alert>
            <Button
              onClick={fetchOrganizations}
              variant="contained"
              color="primary"
              sx={{ width: 'fit-content' }}
            >
              Retry
            </Button>
          </Stack>
        </Box>
      )}

      <Paper elevation={2} sx={{ width: '100%', minHeight: '200px' }}>
        <DataGrid
          rowHeight={52}
          rows={organizations}
          columns={orgCols}
          slots={{ toolbar: CustomToolbar, pagination: CustomPagination }}
          slotProps={{
            basePopper: { placement: 'bottom-start' },
            toolbar: { disableExport: true } as any,
            columnsManagement: {
              disableResetButton: true,
              getTogglableColumns: (columns) => {
                const alwaysVisible = ['name'];
                return columns
                  .filter(
                    (col) => col.field && !alwaysVisible.includes(col.field)
                  )
                  .map((col) => col.field as string);
              }
            }
          }}
          loading={isLoading}
          paginationMode="server"
          rowCount={rowCount}
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          filterMode="server"
          filterModel={filterModel}
          onFilterModelChange={(m) => {
            setFilterModel(m);
            setPaginationModel((prev) => ({ ...prev, page: 0 }));
          }}
          sortingMode="server"
          sortModel={sortModel}
          onSortModelChange={(m) => {
            setSortModel(m);
            setPaginationModel((prev) => ({ ...prev, page: 0 }));
          }}
          initialState={{
            pagination: { paginationModel: { pageSize: 15, page: 0 } }
          }}
          pageSizeOptions={[15, 30, 50, 100]}
          disableRowSelectionOnClick
          showToolbar
        />
      </Paper>

      <OrganizationForm
        onSubmit={onSubmit}
        open={dialogOpen}
        setOpen={setDialogOpen}
        type="create"
        chosenTags={chosenTags}
        setChosenTags={setChosenTags}
      />
      <InfoDialog
        isOpen={infoDialogOpen}
        handleClick={() => {
          setInfoDialogOpen(false);
          setChosenTags([]);
        }}
        icon={<CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />}
        title={<Typography variant="h4">Success </Typography>}
        content={
          <Typography variant="body1">
            The new organization was successfully added.
          </Typography>
        }
      />
    </Box>
  );
};

export default Organizations;
