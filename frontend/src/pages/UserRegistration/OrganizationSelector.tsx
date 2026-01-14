import React, { useState, useEffect } from 'react';
import { DataGrid, GridRowSelectionModel, GridToolbar } from '@mui/x-data-grid';
import Paper from '@mui/material/Paper';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import { Organization as OrganizationType } from 'types';
import { ENDPOINTS } from '@/constants/endpoints';
import { useAuthContext } from 'context';
import { organizationCols as orgCols } from './UserRegistrationColumns';

export interface OrganizationSelectorProps {
  regionId: string | null | undefined;
  onSelectionChange: (selectedOrgId: string | null) => void;
  initialOrgId?: string;
  errorStates?: {
    getOrgsError: string;
    getUpdateError: string;
  };
  selectedOrg?: GridRowSelectionModel;
  selectedUser?: { full_name: string };
}

export const OrganizationSelector: React.FC<OrganizationSelectorProps> = ({
  regionId,
  onSelectionChange,
  initialOrgId,
  selectedUser
}) => {
  const { apiGet } = useAuthContext();
  const [loading, setLoading] = useState<boolean>(false);
  const [organizations, setOrganizations] = useState<OrganizationType[]>([]);
  const [internalErrorStates, setInternalErrorStates] = useState({
    getOrgsError: '',
    getUpdateError: ''
  });

  // Local state to manage the grid selection, matching your original logic
  const [localSelectedOrg, setLocalSelectedOrg] =
    useState<GridRowSelectionModel>({
      type: 'include',
      ids: new Set<string | number>(initialOrgId ? [initialOrgId] : [])
    });

  const fetchOrganizations = React.useCallback(async () => {
    if (!regionId) {
      setOrganizations([]);
      setInternalErrorStates((prev) => ({
        ...prev,
        getOrgsError: 'This user has no region assigned.'
      }));
      return;
    }
    setLoading(true);
    try {
      const rows = await apiGet<OrganizationType[]>(
        ENDPOINTS.ORGANIZATIONS_REGION.replace('{region_id}', regionId)
      );
      setOrganizations(rows);
      setInternalErrorStates({ getOrgsError: '', getUpdateError: '' });
      setLoading(false);
    } catch (e: any) {
      setInternalErrorStates((prev) => ({ ...prev, getOrgsError: e.message }));
      setLoading(false);
    }
  }, [regionId, apiGet]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  const onRowSelectionModelChange = (
    newRowSelectionModel: GridRowSelectionModel
  ) => {
    const newIds = Array.isArray(newRowSelectionModel)
      ? newRowSelectionModel
      : Array.from(newRowSelectionModel.ids);

    let finalId: string | null = null;

    if (newIds.length > 1) {
      const lastSelected = newIds[newIds.length - 1];
      finalId = lastSelected.toString();
      setLocalSelectedOrg({
        type: 'include',
        ids: new Set([lastSelected])
      });
    } else if (newIds.length === 1) {
      finalId = newIds[0].toString();
      setLocalSelectedOrg({
        type: 'include',
        ids: new Set(newIds)
      });
    } else {
      setLocalSelectedOrg({
        type: 'include',
        ids: new Set()
      });
    }
    // Pass the ID back up to the parent
    onSelectionChange(finalId);
  };

  return (
    <>
      <Typography mb={3}>
        To complete the approval process, select one organization for this user
        to join.
      </Typography>
      <Paper sx={{ height: 600, margin: 'auto' }}>
        <DataGrid
          checkboxSelection
          onRowSelectionModelChange={onRowSelectionModelChange}
          rowSelectionModel={localSelectedOrg}
          rows={organizations ?? []}
          columns={orgCols}
          slots={{ toolbar: GridToolbar }}
          slotProps={{
            toolbar: {
              showQuickFilter: false,
              csvOptions: { disableToolbarButton: true },
              printOptions: { disableToolbarButton: true }
            }
          }}
          sx={{
            '& .MuiDataGrid-columnHeaderCheckbox .MuiDataGrid-columnHeaderTitleContainer':
              {
                display: 'none'
              }
          }}
          disableRowSelectionOnClick
          showToolbar
          loading={loading}
        />
      </Paper>

      {internalErrorStates.getOrgsError && (
        <Alert severity="error">
          Error retrieving organizations: {internalErrorStates.getOrgsError}
        </Alert>
      )}

      {localSelectedOrg.ids.size !== 0 &&
        internalErrorStates.getUpdateError.length === 0 && (
          <Alert severity="info" sx={{ mt: 2 }}>
            {selectedUser?.full_name} will become a member of the selected
            organization.
          </Alert>
        )}
    </>
  );
};

export default OrganizationSelector;
