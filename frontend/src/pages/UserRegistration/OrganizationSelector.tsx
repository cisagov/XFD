import React, { useState, useEffect } from 'react';
import { DataGrid, GridRowSelectionModel, GridToolbar } from '@mui/x-data-grid';
import Alert from '@mui/material/Alert';
import Autocomplete from '@mui/material/Autocomplete';
import Grid from '@mui/material/Grid';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { Organization as OrganizationType } from 'types';
import { ENDPOINTS } from '@/constants/endpoints';
import { useAuthContext } from 'context';
import { organizationCols as orgCols } from './UserRegistrationColumns';
import { User } from 'types';
import { REGION_STATE_MAP, STATE_OPTIONS } from '@/constants/constants';
import { ElevationControl } from '../Users/ElevationControl';
export interface OrganizationSelectorProps {
  regionId: string | null | undefined;
  onSelectionChange: (organization: OrganizationType | null) => void;
  initialOrgId?: string;
  selectedOrg?: GridRowSelectionModel;
  selectedUser: User;
  selectUser?: (user: User) => void;
  formattedUserType?: string;
  getUpdateError?: string;
  pendingUsers: User[];
  isRoleElevationConfirmed: boolean;
  setIsRoleElevationConfirmed: React.Dispatch<React.SetStateAction<boolean>>;
  confirmGlobalAdminChange: string | undefined;
  setConfirmGlobalAdminChange: React.Dispatch<React.SetStateAction<string>>;
}

export const OrganizationSelector: React.FC<OrganizationSelectorProps> = ({
  regionId,
  onSelectionChange,
  initialOrgId,
  selectedUser,
  selectUser,
  formattedUserType,
  getUpdateError,
  pendingUsers,
  isRoleElevationConfirmed,
  setIsRoleElevationConfirmed,
  confirmGlobalAdminChange = '',
  setConfirmGlobalAdminChange
}) => {
  const { apiGet } = useAuthContext();
  const [loading, setLoading] = useState<boolean>(false);
  const [organizations, setOrganizations] = useState<OrganizationType[]>([]);
  const [organizationsError, setOrganizationsError] = useState('');
  const editedUser = pendingUsers.find(
    (userItem: User) => userItem.id === selectedUser.id
  );
  const userRoleChanged = editedUser?.user_type !== selectedUser.user_type;
  // Local state to manage the grid selection, matching your original logic
  const [localSelectedOrg, setLocalSelectedOrg] =
    useState<GridRowSelectionModel>({
      type: 'include',
      ids: new Set<string | number>(initialOrgId ? [initialOrgId] : [])
    });
  useEffect(() => {
    setLocalSelectedOrg({
      type: 'include',
      ids: new Set<string | number>(initialOrgId ? [initialOrgId] : [])
    });
  }, [initialOrgId]);

  const fetchOrganizations = React.useCallback(async () => {
    if (!regionId) {
      setOrganizations([]);
      setOrganizationsError('This user has no region assigned.');
      return;
    }
    setLoading(true);
    try {
      const orgData = await apiGet<OrganizationType[]>(
        ENDPOINTS.ORGANIZATIONS_REGION.replace('{region_id}', regionId)
      );
      const rows = orgData.filter(
        (org) => org.state_name === selectedUser?.state
      );
      setOrganizations(rows);
      setOrganizationsError('');
      if (initialOrgId) {
        const initialOrg = rows.find((org) => org.id === initialOrgId);
        if (initialOrg) {
          onSelectionChange(initialOrg);
        }
      }
      setLoading(false);
    } catch (e: any) {
      setOrganizationsError(e.message);
      setLoading(false);
    }
  }, [regionId, apiGet, initialOrgId, onSelectionChange, selectedUser?.state]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  const onRowSelectionModelChange = React.useCallback(
    (newRowSelectionModel: GridRowSelectionModel) => {
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
      // Pass the full object back up to the parent
      const selectedOrgData =
        organizations.find((org) => org.id === finalId) || null;
      // Pass the full object (including name and acronym) back to the parent
      onSelectionChange(selectedOrgData);
    },
    [onSelectionChange, organizations]
  );

  return (
    <>
      <Typography mb={3}>
        To complete the approval process, ensure the user is in the correct
        state and select one organization for this user to join.
      </Typography>
      <Grid container spacing={5} mb={2}>
        <Grid size={{ xs: 12, sm: 5 }}>
          <Typography mb={1}>State</Typography>
          <Autocomplete
            id="state"
            size="small"
            options={STATE_OPTIONS}
            value={selectedUser?.state || null}
            onChange={(_, newValue) => {
              if (!selectedUser || !selectUser) {
                return;
              }
              selectUser({
                ...selectedUser,
                state: newValue || '',
                region_id: newValue ? REGION_STATE_MAP[String(newValue)] : ''
              });
            }}
            renderInput={(params) => <TextField {...params} label="State" />}
            isOptionEqualToValue={(option, value) => option === value}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6 }}>
          <Typography mb={1}>User Type</Typography>
          <RadioGroup
            aria-label="User Type"
            name="user_type"
            value={selectedUser?.user_type}
            onChange={(event) => {
              if (!selectedUser || !selectUser) {
                return;
              }
              selectUser({
                ...selectedUser,
                user_type: event.target.value as User['user_type']
              });
              setIsRoleElevationConfirmed(false);
            }}
          >
            <FormControlLabel
              value="standard"
              control={<Radio color="primary" />}
              label="Standard"
            />
            <FormControlLabel
              value="globalView"
              control={<Radio color="primary" />}
              label="Global View"
              disabled={formattedUserType !== 'Global Admin'}
            />
            <FormControlLabel
              value="regionalAdmin"
              control={<Radio color="primary" />}
              label="Regional Administrator"
              disabled={formattedUserType !== 'Global Admin'}
            />
            <FormControlLabel
              value="globalAdmin"
              control={<Radio color="primary" />}
              label="Global Administrator"
              disabled={formattedUserType !== 'Global Admin'}
            />
          </RadioGroup>
          <ElevationControl
            confirmGlobalAdminChange={confirmGlobalAdminChange}
            setConfirmGlobalAdminChange={setConfirmGlobalAdminChange}
            userRoleChanged={userRoleChanged}
            values={selectedUser}
            isRoleElevationConfirmed={isRoleElevationConfirmed}
            setIsRoleElevationConfirmed={setIsRoleElevationConfirmed}
          />
        </Grid>
      </Grid>
      <Paper sx={{ height: 400, margin: 'auto' }}>
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

      {organizationsError.length > 0 && (
        <Alert severity="error">
          Error retrieving organizations: {organizationsError}
        </Alert>
      )}
      {getUpdateError && getUpdateError.length > 0 && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Error updating pending user: {getUpdateError}
        </Alert>
      )}

      {localSelectedOrg.ids.size !== 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {selectedUser?.full_name} will become a member of the selected
          organization.
        </Alert>
      )}
    </>
  );
};

export default OrganizationSelector;
