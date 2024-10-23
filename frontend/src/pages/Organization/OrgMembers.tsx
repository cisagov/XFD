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

type MemberRow = {
  row: {
    approved?: Boolean;
    role?: String;
    user: { fullName?: String; email?: String; invitePending?: String };
  };
};

export const OrgMembers: React.FC<OrgMemberProps> = ({
  organization,
  userRoles,
  setUserRoles
}) => {
  const { apiPost } = useAuthContext();
  const [removeUserDialogOpen, setRemoveUserDialogOpen] = React.useState(false);
  const [infoDialogOpen, setInfoDialogOpen] = React.useState(false);
  const [selectedRow, setSelectedRow] = React.useState<Role>();
  const [hasError, setHasError] = React.useState('');

  const userRoleColumns: GridColDef[] = [
    {
      headerName: 'Name',
      field: 'fullName',
      valueGetter: (params: MemberRow) => params.row?.user?.fullName,
      flex: 1
    },
    {
      headerName: 'Email',
      field: 'email',
      valueGetter: (params: MemberRow) => params.row?.user?.email,
      flex: 1.5
    },
    {
      headerName: 'Role',
      field: 'role',
      valueGetter: (params: MemberRow) => {
        if (params.row?.approved) {
          if (params.row?.user?.invitePending) {
            return 'Invite pending';
          } else if (params.row?.role === 'admin') {
            return 'Administrator';
          } else {
            return 'Member';
          }
        }
      },
      flex: 1
    },
    {
      headerName: 'Remove',
      field: 'remove',
      flex: 0.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        const descriptionId = `description-${cellValues.row.id}`;
        const description = `Remove ${cellValues.row.user?.fullName} from ${organization?.name}`;
        return (
          <React.Fragment>
            <span id={descriptionId} style={{ display: 'none' }}>
              {description}
            </span>
            <IconButton
              color="error"
              aria-label={description}
              aria-describedby={descriptionId}
              onClick={() => {
                const userRole = userRoles.find(
                  (role: { user: { id: String } }) =>
                    role.user.id === cellValues.row.user.id
                );
                setSelectedRow(userRole);
                setRemoveUserDialogOpen(true);
              }}
            >
              <RemoveCircleOutline />
            </IconButton>
          </React.Fragment>
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
          rows={userRoles}
          columns={userRoleColumns}
          slots={{ toolbar: CustomToolbar }}
          initialState={{
            pagination: { paginationModel: { pageSize: 15 } }
          }}
          pageSizeOptions={[15, 30, 50, 100]}
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
              <b>{selectedRow?.user.fullName}</b> from{' '}
              <b>{organization.name}</b> and cannot be undone.
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
            {selectedRow?.user.fullName} has been removed from{' '}
            {organization.name}
          </Typography>
        }
      />
    </Box>
  );
};

export default OrgMembers;
