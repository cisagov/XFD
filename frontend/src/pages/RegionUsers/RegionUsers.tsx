import React, { useState, useEffect, useCallback } from 'react';
import { initializeUser, User, Organization as OrganizationType } from 'types';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import { ExportCustomerMetricsButton } from '@components/Metrics/Widgets/ExportCustomerMetricsButton';
import InfoDialog from 'components/Dialog/InfoDialog';
import { useAuthContext } from 'context';
import { Alert, Box, Button, Paper, Stack, Typography } from '@mui/material';
import {
  DataGrid,
  GridColDef,
  GridRenderCellParams,
  GridRowSelectionModel,
  GridToolbar,
  useGridApiRef
} from '@mui/x-data-grid';
import DoneIcon from '@mui/icons-material/Done';
import { CheckCircleOutline as CheckIcon } from '@mui/icons-material';
import CloseIcon from '@mui/icons-material/Close';
import { useUserLevel } from 'hooks/useUserLevel';
import { formatDate, parseISO } from 'date-fns';

type DialogStates = {
  isOrgDialogOpen: boolean;
  isDenyDialogOpen: boolean;
  isApproveDialogOpen: boolean;
  isInfoDialogOpen: boolean;
};

type ErrorStates = {
  getOrgsError: string;
  getUsersError: string;
  getUpdateError: string;
  getDeleteError: string;
};

type CloseReason = 'backdropClick' | 'escapeKeyDown' | 'closeButtonClick';

const transformData = (data: User[]): User[] => {
  return data.map(({ roles, ...user }) => ({
    ...user,
    roles,
    organizations: roles.map((role) => ' ' + role.organization.name),
    organizations_display: roles
      .map((role) => role.organization.name)
      .join(', '),
    last_logged_in: user.last_logged_in
      ? formatDate(parseISO(user.last_logged_in), 'MM/dd/yyyy hh:mm a')
      : 'None'
  }));
};
export const RegionUsers: React.FC = () => {
  const { apiDelete, apiGet, apiPost, apiPut, user } = useAuthContext();
  const apiRefPendingUsers = useGridApiRef();
  const apiRefCurrentUsers = useGridApiRef();
  const regionalAdminId = user?.region_id;
  const { formattedUserType } = useUserLevel();
  const getOrgsURL = `/organizations/region_id/`;
  const getUsersURL = `/v2/users?invite_pending=`;

  const pendingCols: GridColDef[] = [
    {
      field: 'full_name',
      headerName: 'Name',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Full Name for User: ${cellValues.row.full_name}`}
          >
            {cellValues.row.full_name}
          </Box>
        );
      }
    },
    {
      field: 'email',
      headerName: 'Email',
      minWidth: 100,
      flex: 2,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Email for User ${cellValues.row.full_name}: ${cellValues.row.email}`}
          >
            {cellValues.row.email}
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
            aria-label={`State for User ${cellValues.row.full_name}: ${cellValues.row.state}`}
          >
            {cellValues.row.state}
          </Box>
        );
      }
    },
    {
      field: 'created_at',
      headerName: 'Created At',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Created At Date for User ${cellValues.row.full_name}: ${cellValues.row.created_at}`}
          >
            {cellValues.row.created_at}
          </Box>
        );
      }
    },
    {
      field: 'cognito_use_case_description',
      headerName: 'Use Case',
      minWidth: 255,
      flex: 1.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Use Case for ${cellValues.row.full_name}: ${cellValues.row.cognito_use_case_description}`}
          >
            {cellValues.row.cognito_use_case_description}
          </Box>
        );
      }
    },
    {
      field: 'status',
      headerName: 'Registration Status',
      minWidth: 250,
      flex: 2,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Stack direction="row" spacing={1} mt={1}>
            <Button
              variant="contained"
              endIcon={<DoneIcon />}
              color="success"
              onClick={() => handleApproveClick(cellValues.row)}
              disabled={user?.user_type === 'globalView'}
              aria-label={`Approve User: ${cellValues.row.full_name}`}
            >
              Approve
            </Button>
            <Button
              variant="contained"
              endIcon={<CloseIcon />}
              color="error"
              onClick={() => handleDenyClick(cellValues.row)}
              disabled={user?.user_type === 'globalView'}
              aria-label={`Deny User: ${cellValues.row.full_name}`}
            >
              Deny
            </Button>
          </Stack>
        );
      }
    }
  ];
  const memberCols: GridColDef[] = [
    {
      field: 'full_name',
      headerName: 'Name',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Full Name for User: ${cellValues.row.full_name}`}
          >
            {cellValues.row.full_name}
          </Box>
        );
      }
    },
    {
      field: 'email',
      headerName: 'Email',
      minWidth: 100,
      flex: 2,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Email for User ${cellValues.row.full_name}: ${cellValues.row.email}`}
          >
            {cellValues.row.email}
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
            aria-label={`State for User ${cellValues.row.full_name}: ${cellValues.row.state}`}
          >
            {cellValues.row.state}
          </Box>
        );
      }
    },
    {
      field: 'last_logged_in',
      headerName: 'Last Logged In',
      minWidth: 100,
      flex: 1.5,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Last Logged In Date for User ${cellValues.row.full_name}: ${cellValues.row.last_logged_in}`}
          >
            {cellValues.row.last_logged_in}
          </Box>
        );
      }
    },
    {
      field: 'organizations_display',
      headerName: 'Organizations',
      minWidth: 250,
      flex: 2,
      renderCell: (cellValues: GridRenderCellParams) => (
        <Box
          component="span"
          aria-label={`Organizations for User ${cellValues.row.full_name}: ${cellValues.row.organizations_display}`}
        >
          {cellValues.row.organizations_display}
        </Box>
      )
    }
  ];
  const regionIdColumn = {
    field: 'region_id',
    headerName: 'Region',
    minWidth: 100,
    flex: 0.5,
    renderCell: (cellValues: GridRenderCellParams) => {
      return (
        <Box
          component="span"
          aria-label={`Region ID for User ${cellValues.row.full_name}: ${cellValues.row.region_id}`}
        >
          {cellValues.row.region_id}
        </Box>
      );
    }
  };
  if (user?.user_type !== 'regionalAdmin') {
    pendingCols.unshift(regionIdColumn);
    memberCols.unshift(regionIdColumn);
  }
  const orgCols: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
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
      field: 'updated_at',
      headerName: 'Updated At',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`Date Updated At for Organization ${cellValues.row.name}: ${cellValues.row.updated_at}`}
          >
            {cellValues.row.updated_at}
          </Box>
        );
      }
    },
    {
      field: 'state_name',
      headerName: 'State',
      minWidth: 100,
      flex: 1,
      renderCell: (cellValues: GridRenderCellParams) => {
        return (
          <Box
            component="span"
            aria-label={`State Name for Organization ${cellValues.row.name}: ${cellValues.row.state_name}`}
          >
            {cellValues.row.state_name}
          </Box>
        );
      }
    }
  ];
  const [dialogStates, setDialogStates] = useState<DialogStates>({
    isOrgDialogOpen: false,
    isDenyDialogOpen: false,
    isApproveDialogOpen: false,
    isInfoDialogOpen: false
  });
  const [errorStates, setErrorStates] = useState<ErrorStates>({
    getOrgsError: '',
    getUsersError: '',
    getUpdateError: '',
    getDeleteError: ''
  });
  const [selectedUser, selectUser] = useState<User>(initializeUser);
  const [selectedOrg, setSelectedOrg] = React.useState<GridRowSelectionModel>({
    type: 'include',
    ids: new Set<string | number>()
  });
  const [organizations, setOrganizations] = useState<OrganizationType[]>([]);
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [currentUsers, setCurrentUsers] = useState<User[]>([]);
  const [infoDialogContent, setInfoDialogContent] = useState<String>('');

  const fetchOrganizations = async (row: User) => {
    if (!row.region_id) {
      setOrganizations([]);
      setErrorStates((prev) => ({
        ...prev,
        getOrgsError: 'This user has no region assigned.'
      }));
      return;
    }
    try {
      const rows = await apiGet<OrganizationType[]>(getOrgsURL + row.region_id);
      setOrganizations(rows);
      if (row.roles.length > 0) {
        setSelectedOrg({
          type: 'include',
          ids: new Set([row.roles[0].organization.id])
        });
      }
      setErrorStates({ ...errorStates, getOrgsError: '', getUpdateError: '' });
    } catch (e: any) {
      setErrorStates({ ...errorStates, getOrgsError: e.message });
    }
  };
  const fetchPendingUsers = useCallback(async () => {
    try {
      const rows = await apiGet<User[]>(
        user?.user_type === 'regionalAdmin'
          ? `${getUsersURL}true&region_id=${regionalAdminId}`
          : `${getUsersURL}true`
      );
      setPendingUsers(rows);
      setErrorStates({ ...errorStates, getUsersError: '' });
    } catch (e: any) {
      setErrorStates({ ...errorStates, getUsersError: e.message });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiGet]);
  const fetchCurrentUsers = useCallback(async () => {
    try {
      const rows = await apiGet<User[]>(
        user?.user_type === 'regionalAdmin'
          ? `${getUsersURL}false&region_id=${regionalAdminId}`
          : `${getUsersURL}false`
      );
      setCurrentUsers(transformData(rows));
      setErrorStates({ ...errorStates, getUsersError: '' });
    } catch (e: any) {
      setErrorStates({ ...errorStates, getUsersError: e.message });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiGet]);

  useEffect(() => {
    fetchPendingUsers();
    fetchCurrentUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const deleteUser = useCallback(
    (user_id: string): Promise<boolean> => {
      return apiDelete(`/users/${user_id}`).then(
        () => {
          apiRefPendingUsers.current?.updateRows([
            { id: user_id, _action: 'delete' }
          ]);
          setPendingUsers((prevPendingUsers) =>
            prevPendingUsers.filter((user) => user.id !== user_id)
          );
          setInfoDialogContent('This user has been successfully removed.');
          return true;
        },
        (e) => {
          setErrorStates({ ...errorStates, getDeleteError: e.message });
          return false;
        }
      );
    }, // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiDelete]
  );

  const addOrgToUser = useCallback(
    (user_id: string, selectedOrgId: any): Promise<boolean> => {
      return apiPost(`/v2/organizations/${selectedOrgId}/users`, {
        body: { user_id, role: 'user' }
      }).then(
        (res) => {
          return updateUser(user_id, res.organization.name);
        },
        (e) => {
          setErrorStates({ ...errorStates, getUpdateError: e.message });
          return false;
        }
      );
    }, // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiPost]
  );

  const updateUser = useCallback(
    (user_id: string, org_name: string): Promise<boolean> => {
      return apiPost(`/v2/update_user/${user_id}`, {
        body: { invite_pending: false }
      }).then(
        (res) => {
          apiRefPendingUsers.current?.updateRows([
            { id: user_id, _action: 'delete' }
          ]);
          setPendingUsers((prevPendingUsers) =>
            prevPendingUsers.filter((user) => user.id !== user_id)
          );
          res['organizations'] = org_name;
          apiRefCurrentUsers.current?.updateRows([res]);
          setCurrentUsers((prevCurrentUsers) => [...prevCurrentUsers, res]);
          return sendApprovalEmail(user_id);
        },
        (e) => {
          setErrorStates({ ...errorStates, getUpdateError: e.message });
          return false;
        }
      );
    }, // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiPut]
  );

  const sendApprovalEmail = useCallback(
    (user_id: string): Promise<boolean> => {
      return apiPost(`/users/${user_id}/register/approve`).then(
        (res) => {
          console.log(res);
          return true;
        },
        (e) => {
          console.log(e);
          return false;
        }
      );
    }, // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiPost]
  );

  const handleCloseDialog = (value: CloseReason) => {
    if (value === 'backdropClick' || value === 'escapeKeyDown') {
      return;
    }
    setDialogStates({
      ...dialogStates,
      isOrgDialogOpen: false
    });
    selectUser(initializeUser);
  };

  const handleConfirmDenyClick = async () => {
    const success = await deleteUser(selectedUser.id);
    if (success) {
      setDialogStates({
        ...dialogStates,
        isDenyDialogOpen: false,
        isInfoDialogOpen: true
      });
    }
  };

  const handleApproveClick = (row: typeof initializeUser) => {
    setSelectedOrg({
      type: 'include',
      ids: new Set<string | number>()
    });
    setDialogStates({
      ...dialogStates,
      isOrgDialogOpen: true
    });
    selectUser(row);
    fetchOrganizations(row);
  };

  const handleDenyClick = (row: typeof initializeUser) => {
    setDialogStates({
      ...dialogStates,
      isDenyDialogOpen: true
    });
    selectUser(row);
  };

  const handleDenyCancelClick = () => {
    setDialogStates((prevState) => ({
      ...prevState,
      isDenyDialogOpen: false
    }));
  };

  const handleApproveCancelClick = () => {
    setDialogStates((prevState) => ({
      ...prevState,
      isOrgDialogOpen: false
    }));
    selectUser(initializeUser);
  };

  const removeOrgFromUser = useCallback(
    (org_id: String, roleId: String) => {
      apiPost(`/organizations/${org_id}/roles/${roleId}/remove`, {
        body: {}
      }).then(
        (res) => {
          console.log(res);
        },
        (e) => {
          setErrorStates({ ...errorStates, getUpdateError: e.message });
        }
      );
    }, // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiPost]
  );

  const handleApproveConfirmClick = async () => {
    try {
      const userHadOrg = selectedUser.roles.length > 0;
      const originalOrgId = userHadOrg
        ? selectedUser.roles[0].organization.id
        : '';
      const selectedOrgId =
        selectedOrg.ids.size > 0
          ? Array.from(selectedOrg.ids)[0].toString()
          : null;
      let success = false;
      // If the user's org was already added and not modified, only update the user.
      if (userHadOrg && originalOrgId === selectedOrgId) {
        success = await updateUser(
          selectedUser.id,
          selectedUser.roles[0].organization.name
        );
        // If the user now has a different org than before, remove the previous org.
      } else if (userHadOrg && originalOrgId !== selectedOrgId) {
        // TODO: Make a new API endpoint to update Org for User instead of doing a removal and addition.
        removeOrgFromUser(originalOrgId, selectedUser.roles[0].id);
        success = await addOrgToUser(selectedUser.id, selectedOrgId);
        // If the previous operation was successful or if the user had no previous org,
        // add the user to the selected org which then also updates the user.
      } else {
        success = await addOrgToUser(selectedUser.id, selectedOrgId);
      }
      if (success) {
        handleCloseDialog('closeButtonClick');
        setDialogStates((prevState) => ({
          ...prevState,
          isInfoDialogOpen: true
        }));
        setInfoDialogContent(
          `The user has been approved and is a member of Region ${selectedUser.region_id}.`
        );
      } else {
        throw new Error('Failed to approve the user.');
      }
    } catch (e: any) {
      setErrorStates({ ...errorStates, getUpdateError: e.message });
    }
  };
  const onRowSelectionModelChange = (
    newRowSelectionModel: GridRowSelectionModel
  ) => {
    const newIds = Array.isArray(newRowSelectionModel)
      ? newRowSelectionModel
      : Array.from(newRowSelectionModel.ids);

    if (newIds.length > 1) {
      const lastSelected = newIds[newIds.length - 1];
      setSelectedOrg({
        type: 'include',
        ids: new Set([lastSelected])
      });
    } else if (newIds.length === 1) {
      setSelectedOrg({
        type: 'include',
        ids: new Set(newIds)
      });
    } else {
      setSelectedOrg({
        type: 'include',
        ids: new Set()
      });
    }
  };

  return (
    <Box
      display="flex"
      flexDirection="column"
      minHeight="100vh"
      maxWidth="1152px"
      width="100%"
      margin="auto"
    >
      <Box sx={{ px: 2, py: 5 }}>
        <Typography variant="h1" style={{ fontSize: '2.125rem' }}>
          {`${formattedUserType} Dashboard`}
        </Typography>
        <br />
        <ExportCustomerMetricsButton />
        <Typography variant="h2" style={{ fontSize: '1.25rem' }} pb={2} pt={2}>
          Pending Requests
        </Typography>
        <Paper sx={{ height: '387px' }}>
          <DataGrid
            apiRef={apiRefPendingUsers}
            columns={pendingCols}
            rows={pendingUsers}
            disableRowSelectionOnClick
            autoPageSize
          />
        </Paper>
        {errorStates.getUsersError && (
          <Alert severity="error">
            Error retrieving users from the database:{' '}
            {errorStates.getUsersError}
          </Alert>
        )}
        <Typography variant="h2" style={{ fontSize: '1.25rem' }} pb={2} pt={5}>
          Members of
          {user?.user_type === 'regionalAdmin'
            ? ` Region ${regionalAdminId}`
            : ' all regions'}
        </Typography>
        <Paper sx={{ height: '667px' }}>
          <DataGrid
            apiRef={apiRefCurrentUsers}
            columns={memberCols}
            rows={currentUsers}
            disableRowSelectionOnClick
            slots={{ toolbar: GridToolbar }}
            autoPageSize
            showToolbar
          />
        </Paper>
      </Box>
      <ConfirmDialog
        isOpen={dialogStates.isOrgDialogOpen}
        onClose={(_, reason) => handleCloseDialog(reason)}
        onConfirm={handleApproveConfirmClick}
        onCancel={handleApproveCancelClick}
        title={`Add ${selectedUser.full_name} to an organization in Region ${selectedUser.region_id}`}
        content={
          <>
            <Typography mb={3}>
              To complete the approval process, select one organization for this
              user to join.
            </Typography>
            <Paper sx={{ height: 600, margin: 'auto' }}>
              <DataGrid
                checkboxSelection
                onRowSelectionModelChange={onRowSelectionModelChange}
                rowSelectionModel={selectedOrg}
                rows={organizations ?? []}
                columns={orgCols}
                slots={{ toolbar: GridToolbar }}
                slotProps={{
                  toolbar: {
                    showQuickFilter: true
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
              />
            </Paper>
            {errorStates.getOrgsError && (
              <Alert severity="error">
                Error retrieving organizations: {errorStates.getOrgsError}
              </Alert>
            )}
            {selectedOrg.ids.size !== 0 &&
              errorStates.getUpdateError.length === 0 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  {selectedUser.full_name} will become a member of the selected
                  organization.
                </Alert>
              )}
            {errorStates.getUpdateError.length !== 0 && (
              <Alert severity="error">
                Error updating user: {errorStates.getUpdateError}. See the
                network tab for more details.
              </Alert>
            )}
          </>
        }
        disabled={selectedOrg.ids.size === 0}
        screenWidth="lg"
      />
      <ConfirmDialog
        isOpen={dialogStates.isDenyDialogOpen}
        onConfirm={handleConfirmDenyClick}
        onCancel={handleDenyCancelClick}
        title={`Are you sure?`}
        content={
          <>
            <Typography mb={3}>
              Denying this request will permanently remove{' '}
              {selectedUser.full_name} from the records and cannot be undone.
            </Typography>
            {errorStates.getDeleteError && (
              <Alert severity="error">
                Error removing user: {errorStates.getDeleteError}. See the
                network tab for more details.
              </Alert>
            )}
          </>
        }
      />
      <InfoDialog
        isOpen={dialogStates.isInfoDialogOpen}
        handleClick={() => {
          setDialogStates((prevState) => ({
            ...prevState,
            isInfoDialogOpen: false
          }));
        }}
        icon={<CheckIcon color="success" sx={{ fontSize: '80px' }} />}
        title={<Typography variant="h4">Success </Typography>}
        content={<Typography variant="body1">{infoDialogContent}</Typography>}
      />
    </Box>
  );
};

export default RegionUsers;
