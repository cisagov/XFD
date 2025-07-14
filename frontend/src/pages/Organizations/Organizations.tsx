import React, { useCallback, useEffect, useState } from 'react';
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
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { useHistory } from 'react-router-dom';
import { CheckCircleOutline } from '@mui/icons-material';
import { OrganizationForm } from './OrganizationForm';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import InfoDialog from 'components/Dialog/InfoDialog';

export const Organizations: React.FC = () => {
  const { apiGet, apiPost, setFeedbackMessage, user } = useAuthContext();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loadingError, setLoadingError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [chosenTags, setChosenTags] = useState<string[]>([]);
  const history = useHistory();
  const region_id = user?.region_id;

  const getOrgsUrl = () => {
    if (user?.user_type === 'regionalAdmin') {
      return `/organizations/region_id/${region_id}`;
    }
    return `/v2/organizations`;
  };
  const orgsUrl = getOrgsUrl();

  const fetchOrganizations = useCallback(async () => {
    setIsLoading(true);
    setLoadingError(false);
    try {
      const rows = await apiGet<Organization[]>(orgsUrl);
      setOrganizations(rows);
    } catch (e) {
      console.error(e);
      setLoadingError(true);
    } finally {
      setIsLoading(false);
    }
  }, [apiGet, orgsUrl]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  const orgCols: GridColDef[] = [
    { field: 'name', headerName: 'Organization', minWidth: 100, flex: 2 },
    { field: 'state', headerName: 'State', minWidth: 100, flex: 1 },
    { field: 'region_id', headerName: 'Region', minWidth: 100, flex: 1 },
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
        const ariaLabel = `View or edit organization ${cellValues.row.name}`;
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
      <Box mb={3} mt={3} display="flex" justifyContent="center">
        {isLoading ? (
          <Paper elevation={2}>
            <Alert severity="info">Loading Organizations...</Alert>
          </Paper>
        ) : loadingError ? (
          <Stack direction="row" spacing={2}>
            <Paper elevation={2}>
              <Alert severity="warning">Error Loading Organizations!</Alert>
            </Paper>
            <Button
              onClick={fetchOrganizations}
              variant="contained"
              color="primary"
              sx={{ width: 'fit-content' }}
            >
              Retry
            </Button>
          </Stack>
        ) : (
          <Paper elevation={2} sx={{ width: '100%', minHeight: '200px' }}>
            <DataGrid
              rows={organizations}
              columns={orgCols}
              slots={{ toolbar: CustomToolbar }}
              initialState={{
                pagination: { paginationModel: { pageSize: 15 } }
              }}
              pageSizeOptions={[15, 30, 50, 100]}
            />
          </Paper>
        )}
      </Box>
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
