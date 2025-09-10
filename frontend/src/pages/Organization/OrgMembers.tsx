import React from 'react';
import { useAuthContext } from 'context';
import { Organization as OrganizationType, Role } from 'types';
import { Alert, Box, IconButton, Paper, Typography } from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { CheckCircleOutline, RemoveCircleOutline } from '@mui/icons-material';
import CustomToolbar from 'components/DataGrid/CustomToolbar';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import InfoDialog from 'components/Dialog/InfoDialog';

type OrgMemberProps = {
  organization: OrganizationType;
  userRoles: Role[];
  setUserRoles: Function;
};

const flattenUserRoles = (data: any[]) =>
  data.map((item) => {
    const nestedUser = item.user?.user || item.user || {};
    return {
      id: item.id,
      role: item.role,
      approved: item.approved,
      user_id: nestedUser.id,
      email: nestedUser.email,
      first_name: nestedUser.first_name,
      last_name: nestedUser.last_name,
      full_name: nestedUser.full_name,
      invite_pending: nestedUser.invite_pending
    };
  });

export const OrgMembers: React.FC<OrgMemberProps> = ({
  organization,
  userRoles,
  setUserRoles
}) => {
  const { apiPost, user } = useAuthContext();
  const [removeUserDialogOpen, setRemoveUserDialogOpen] = React.useState(false);
  const [infoDialogOpen, setInfoDialogOpen] = React.useState(false);
  const [selectedRow, setSelectedRow] = React.useState<Role>();
  const [hasError, setHasError] = React.useState('');

  const flatUserRoles = flattenUserRoles(userRoles);

  const userRoleColumns: GridColDef[] = [
    {
      field: 'full_name',
      headerName: 'Name',
      flex: 1
    },
    {
      field: 'email',
      headerName: 'Email',
      flex: 1.5
    },
    {
      field: 'role',
      headerName: 'Role',
      flex: 1
    },
    {
      field: 'remove',
      headerName: 'Remove',
      flex: 0.5,
      sortable: false,
      filterable: false,
      renderCell: (params: GridRenderCellParams) => {
        const descriptionId = `description-${params.row.id}`;
        const description = `Remove ${params.row.full_name}`;
        return (
          <>
            <span id={descriptionId} style={{ display: 'none' }}>
              {description}
            </span>
            <IconButton
              color="error"
              aria-label={description}
              aria-describedby={descriptionId}
              onClick={() => {
                setSelectedRow(params.row);
                setRemoveUserDialogOpen(true);
              }}
            >
              <RemoveCircleOutline />
            </IconButton>
          </>
        );
      }
    }
  ];

  const removeUser = async () => {
    try {
      await apiPost(
        `/organizations/${organization?.id}/roles/${selectedRow?.id}/remove`,
        { body: {} }
      );
      setRemoveUserDialogOpen(false);
      setInfoDialogOpen(true);
    } catch (e) {
      console.error(e);
      setHasError(e + '.');
    }
  };

  const resetStates = () => {
    setInfoDialogOpen(false);
    setRemoveUserDialogOpen(false);
    setHasError('');
    setSelectedRow(undefined);
  };

  return (
    <Box display="flex">
      <Paper elevation={2} sx={{ width: '100%', minHeight: '200px' }}>
        <DataGrid
          rows={flatUserRoles}
          columns={userRoleColumns}
          slots={{ toolbar: CustomToolbar }}
          slotProps={{
            toolbar: { exportTitle: organization?.name + ' Members' } as any,
            basePopper: {
              placement: 'bottom-start'
            }
          }}
          initialState={{
            pagination: { paginationModel: { pageSize: 15 } }
          }}
          pageSizeOptions={[15, 30, 50, 100]}
          disableRowSelectionOnClick={user?.user_type === 'globalView'}
          showToolbar
        />
      </Paper>
      <ConfirmDialog
        isOpen={removeUserDialogOpen}
        onConfirm={removeUser}
        onCancel={resetStates}
        disabled={hasError !== ''}
        title={'Are you sure you want to remove this user?'}
        content={
          <React.Fragment>
            <Typography mb={3}>
              This request will permanently remove{' '}
              <b>{selectedRow?.user?.full_name}</b> from{' '}
              <b>{organization?.name}</b> and cannot be undone.
            </Typography>
            {hasError && (
              <Alert severity="error">
                {hasError} Unable to remove user. See the network tab for more
                details.
              </Alert>
            )}
          </React.Fragment>
        }
        screenWidth="xs"
      />
      <InfoDialog
        isOpen={infoDialogOpen}
        handleClick={() => {
          setUserRoles(
            userRoles.filter(
              (row: { id: String }) => row.id !== selectedRow?.id
            )
          );
          resetStates();
        }}
        icon={<CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />}
        title={<Typography variant="h4">Success</Typography>}
        content={
          <Typography variant="body1">
            {selectedRow?.user?.full_name} has been removed from{' '}
            {organization?.name}
          </Typography>
        }
      />
    </Box>
  );
};

export default OrgMembers;
