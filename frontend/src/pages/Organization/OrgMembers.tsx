import React from 'react';
import { useAuthContext } from 'context';
import { Organization as OrganizationType, Role } from 'types';
// @ts-ignore:next-line
import { IconButton, Paper } from '@mui/material';
import { DataGrid, GridRenderCellParams } from '@mui/x-data-grid';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import CustomToolbar from 'components/DataGrid/CustomToolbar';

type OrgMemberProps = {
  organization: OrganizationType;
  userRoles: Role[];
  setUserRoles: Function;
};

export const OrgMembers: React.FC<OrgMemberProps> = ({
  organization,
  userRoles,
  setUserRoles
}) => {
  const { apiPost } = useAuthContext();

  const userRoleColumns = [
    {
      headerName: 'Name',
      field: 'fullName',
      valueGetter: (params: any) => params.row?.user?.fullName,
      flex: 1
    },
    {
      headerName: 'Email',
      field: 'email',
      valueGetter: (params: any) => params.row?.user?.email,
      flex: 1.5
    },
    {
      headerName: 'Role',
      field: 'role',
      valueGetter: (params: any) => {
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
              onClick={() => removeUser(cellValues.row.user.id)}
            >
              <RemoveCircleOutlineIcon />
            </IconButton>
          </React.Fragment>
        );
      }
    }
  ];

  const removeUser = async (userId: String) => {
    try {
      const userRole = userRoles.find(
        (role: { user: { id: String } }) => role.user.id === userId
      );
      await apiPost(
        `/organizations/${organization?.id}/roles/${userRole?.id}/remove`,
        { body: {} }
      );
      setUserRoles(
        userRoles.filter((row: { id: String }) => row.id !== userRole?.id)
      );
      console.log('The user was successfully removed from the organization.');
    } catch (e) {
      console.error(e);
      console.log(e);
    }
  };

  return (
    <React.Fragment>
      <Paper elevation={0}>
        <DataGrid
          rows={userRoles}
          columns={userRoleColumns}
          slots={{ toolbar: CustomToolbar }}
        />
      </Paper>
    </React.Fragment>
  );
};

export default OrgMembers;
