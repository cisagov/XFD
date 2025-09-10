import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import EditNoteOutlinedIcon from '@mui/icons-material/EditNoteOutlined';
import { Organization } from 'types';
import { useAuthContext } from 'context';
import {
  Alert,
  Box,
  Button,
  IconButton,
  Paper,
  Stack,
  Typography
} from '@mui/material';
import {
  DataGrid,
  GridColDef,
  GridRenderCellParams,
  GridFilterModel,
  GridSortModel
} from '@mui/x-data-grid';
import { useHistory } from 'react-router-dom';
import { CheckCircleOutline } from '@mui/icons-material';
import { OrganizationForm } from './OrganizationForm';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import InfoDialog from 'components/Dialog/InfoDialog';

type OrgsApiResponse = {
  result: Organization[];
  count: number;
  url?: string;
};

export const Organizations: React.FC = () => {
  const { apiPost, setFeedbackMessage, user } = useAuthContext();
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
  const history = useHistory();
  const region_id = user?.region_id;
  const reqIdRef = useRef(0);

  useEffect(() => {
    const h = setTimeout(() => setDebouncedFilterModel(filterModel), 300);
    return () => clearTimeout(h);
  }, [filterModel]);

  const buildFilters = useCallback(
    (model: GridFilterModel) => {
      const filters: Record<string, any> = {};
      model.items.forEach((i) => {
        if (!i.value) return;
        if (i.field === 'name') {
          const v = String(i.value).trim();
          if (v.length >= 2) filters.name = v; // gate short inputs
        }
        if (i.field === 'state') filters.state = String(i.value).trim();
        if (i.field === 'region_id') filters.region_id = String(i.value).trim();
      });
      if (user?.user_type === 'regionalAdmin' && region_id) {
        filters.region_id = region_id;
      }
      return filters;
    },
    [user?.user_type, region_id]
  );

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
      const data = await apiPost<OrgsApiResponse>('/v2/organizations/search', {
        body: requestBody
      });
      if (myId !== reqIdRef.current) return; // ignore stale responses
      setOrganizations(data.result);
      setRowCount(data.count);
    } catch (e) {
      if (myId === reqIdRef.current) {
        console.error(e);
        setLoadingError(true);
      }
    } finally {
      if (myId === reqIdRef.current) setIsLoading(false);
    }
  }, [apiPost, requestBody]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  const orgCols: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Organization',
      minWidth: 100,
      flex: 2,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Organization Name: ${cellValues.row.name}`}
          >
            {cellValues.row.name}
          </Box>
        );
      }
    },
    {
      field: 'state',
      headerName: 'State',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`State for Organization ${cellValues.row.name}: ${cellValues.row.state}`}
          >
            {cellValues.row.state}
          </Box>
        );
      }
    },
    {
      field: 'region_id',
      headerName: 'Region',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Region for Organization ${cellValues.row.name}: ${cellValues.row.region_id}`}
          >
            {cellValues.row.region_id}
          </Box>
        );
      }
    },
    {
      field: 'view',
      headerName: 'View/Edit',
      minWidth: 100,
      flex: 1,
      disableExport: true,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      renderCell: (cellValues: GridRenderCellParams) => {
        const ariaLabel = `View or Edit Organization ${cellValues.row.name}`;
        const descriptionId = `description-${cellValues.row.id}`;
        return (
          <>
            <span id={descriptionId} style={{ display: 'none' }}>
              {`Edit details for organization ${cellValues.row.name}`}
            </span>
            <IconButton
              color="primary"
              aria-label={ariaLabel}
              aria-describedby={descriptionId}
              onClick={() =>
                history.push('/organizations/' + cellValues.row.id)
              }
            >
              <EditNoteOutlinedIcon />
            </IconButton>
          </>
        );
      }
    }
  ];

  const onSubmit = async (body: Object) => {
    try {
      const org = await apiPost('/organizations', { body });
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
      console.error(e);
    }
  };

  return (
    <Box
      sx={{
        maxWidth: '1152px',
        margin: 'auto',
        px: { xs: 0, sm: 0.5, md: 1, lg: 1, xl: 0 },
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
          rows={organizations}
          columns={orgCols}
          slots={{ toolbar: CustomToolbar }}
          slotProps={{
            basePopper: { placement: 'bottom-start' },
            toolbar: { disableExport: true } as any
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
