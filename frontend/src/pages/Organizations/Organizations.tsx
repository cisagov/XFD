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
import {
  cleanFilterModelItems,
  shouldTriggerFilterUpdate,
  buildOrgFilters
} from '@/utils/tableUtils';

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

  const [sortModel, setSortModel] = useState<GridSortModel>([]);
  const reqIdRef = useRef(0);

  const filterTimerRef = useRef<number | null>(null);

  const [filters, setFilters] = useState<GridFilterModel>({ items: [] });

  const [hasActiveFilters, setHasActiveFilters] = useState(false);

  useEffect(() => {
    return () => {
      if (filterTimerRef.current) {
        clearTimeout(filterTimerRef.current);
        filterTimerRef.current = null;
      }
    };
  }, []);

  const requestBody = useMemo(() => {
    const firstSort = sortModel[0];
    return {
      page: paginationModel.page + 1,
      pageSize: paginationModel.pageSize,
      sort: firstSort?.field || undefined,
      order: firstSort?.sort || undefined,
      filters: buildOrgFilters(filters)
    };
  }, [paginationModel, filters, sortModel]);

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
            toolbar: {
              disableExport: true,
              hasActiveFilters: hasActiveFilters
            } as any,
            panel: {
              onClose: () => {
                // Clear any incomplete filters when the panel closes and fetch unfiltered data.
                // Prevents mismatch between filter model and applied filters.
                const hasIncompleteFilters = filterModel.items.some(
                  (item) => item.value === undefined
                );

                if (hasIncompleteFilters) {
                  setFilterModel({ items: [] });
                  setFilters({ items: [] });
                  setHasActiveFilters(false);
                  setPaginationModel((prev) => ({ ...prev, page: 0 }));
                }
              }
            },
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
          onFilterModelChange={(model) => {
            const cleanedModel = cleanFilterModelItems(model, filterModel);
            setFilterModel(cleanedModel);

            const shouldUpdate = shouldTriggerFilterUpdate(
              cleanedModel.items,
              filterModel.items
            );

            setHasActiveFilters(cleanedModel.items.length !== 0);
            if (!shouldUpdate) {
              return;
            }

            if (filterTimerRef.current) {
              clearTimeout(filterTimerRef.current);
            }

            filterTimerRef.current = window.setTimeout(() => {
              setIsLoading(true);

              setFilters({ items: cleanedModel.items });

              setPaginationModel((prev) => ({ ...prev, page: 0 }));
              filterTimerRef.current = null;
            }, 1000);
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
