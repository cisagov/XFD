import React, { useCallback, useEffect, useState } from 'react';
import EditNoteOutlinedIcon from '@mui/icons-material/EditNoteOutlined';
import { Organization } from 'types';
import { Alert, Box, Button, IconButton, Paper } from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { useHistory } from 'react-router-dom';
import { Add } from '@mui/icons-material';
import { OrganizationForm } from 'components/OrganizationForm';
import { useAuthContext } from 'context';
import CustomToolbar from 'components/DataGrid/CustomToolbar';

export const OrganizationList: React.FC<{
  parent?: Organization;
}> = ({ parent }) => {
  const { apiPost, apiGet, setFeedbackMessage, user } = useAuthContext();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const history = useHistory();
  const regionId = user?.regionId;

  const getOrgsUrl = () => {
    if (user?.userType === 'regionalAdmin') {
      return `/organizations/regionId/${regionId}`;
    } else {
      return `/v2/organizations/`;
    }
  };

  const orgsUrl = getOrgsUrl() as string;

  const orgCols: GridColDef[] = [
    { field: 'name', headerName: 'Organization', minWidth: 100, flex: 2 },
    { field: 'state', headerName: 'State', minWidth: 100, flex: 1 },
    { field: 'regionId', headerName: 'Region', minWidth: 100, flex: 1 },
    {
      field: 'view',
      headerName: 'View/Edit',
      minWidth: 100,
      flex: 1,
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
      const org = await apiPost('/organizations/', {
        body
      });
      setOrganizations(organizations.concat(org));
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422
            ? 'Error when submitting organization entry.'
            : e.message ?? e.toString(),
        type: 'error'
      });
      console.error(e);
    }
  };

  const fetchOrganizations = useCallback(async () => {
    try {
      const rows = await apiGet<Organization[]>(orgsUrl);
      setOrganizations(rows);
    } catch (e) {
      console.error(e);
    }
  }, [apiGet, orgsUrl]);

  useEffect(() => {
    if (!parent) fetchOrganizations();
    else {
      setOrganizations(parent.children);
    }
  }, [fetchOrganizations, parent]);

  const addOrgButton = user?.userType === 'globalAdmin' && (
    <Button
      size="small"
      sx={{ '& .MuiButton-startIcon': { mr: '2px', mb: '2px' } }}
      startIcon={<Add />}
      onClick={() => setDialogOpen(true)}
    >
      Create New Organization
    </Button>
  );

  return (
    <Box mb={3}>
      <Paper elevation={0}>
        {organizations?.length === 0 ? (
          <Alert severity="warning">Unable to load organizations.</Alert>
        ) : (
          <DataGrid
            rows={organizations}
            columns={orgCols}
            slots={{ toolbar: CustomToolbar }}
            slotProps={{
              toolbar: { children: addOrgButton }
            }}
          />
        )}
      </Paper>
      <OrganizationForm
        onSubmit={onSubmit}
        open={dialogOpen}
        setOpen={setDialogOpen}
        type="create"
        parent={parent}
      ></OrganizationForm>
    </Box>
  );
};
