import React, { useState, useEffect, useCallback } from 'react';
import { useTheme } from '@mui/material/styles';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutline';
import InfoOutline from '@mui/icons-material/InfoOutline';
import {
  DataGrid,
  GridRowSelectionModel,
  GridToolbar,
  useGridApiRef
} from '@mui/x-data-grid';
import { User } from 'types';
import { initializeUser } from '@/constants/userAndOrgData';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import { ExportCustomerMetricsButton } from '@components/Metrics/Widgets/ExportCustomerMetricsButton';
import InfoDialog from 'components/Dialog/InfoDialog';
import AlreadyApprovedDialog from 'components/Dialog/AlreadyApprovedDialog';
import { useAuthContext } from 'context';
import { useUserLevel } from 'hooks/useUserLevel';
import { ENDPOINTS } from '@/constants/endpoints';
import { logger } from '@/utils/logger';
import { transformUserData } from '@/utils/transformTableData';
import {
  getPendingUserColumns,
  getMemberUserColumns
} from './UserRegistrationColumns';
import { OrganizationSelector } from './OrganizationSelector';

type DialogStates = {
  isOrgDialogOpen: boolean;
  isDenyDialogOpen: boolean;
  isApproveDialogOpen: boolean;
  isInfoDialogOpen: boolean;
  isUserAlreadyApprovedDialogOpen: boolean;
};

type ErrorStates = {
  getUsersError: string;
  getUpdateError: string;
  getDeleteError: string;
};

type CloseReason = 'backdropClick' | 'escapeKeyDown' | 'closeButtonClick';

export const RegionUsers: React.FC = () => {
  const { apiDelete, apiGet, apiPost, user } = useAuthContext();
  const apiRefPendingUsers = useGridApiRef();
  const apiRefCurrentUsers = useGridApiRef();
  const { formattedUserType } = useUserLevel();
  const getUsersURL = ENDPOINTS.USERS_V2 + '?invite_pending=';
  const theme = useTheme();

  const [dialogStates, setDialogStates] = useState<DialogStates>({
    isOrgDialogOpen: false,
    isDenyDialogOpen: false,
    isApproveDialogOpen: false,
    isInfoDialogOpen: false,
    isUserAlreadyApprovedDialogOpen: false
  });
  const [errorStates, setErrorStates] = useState<ErrorStates>({
    getUsersError: '',
    getUpdateError: '',
    getDeleteError: ''
  });
  const [selectedUser, selectUser] = useState<User>(initializeUser);
  const [selectedOrg, setSelectedOrg] = React.useState<GridRowSelectionModel>({
    type: 'include',
    ids: new Set<string | number>()
  });
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [currentUsers, setCurrentUsers] = useState<User[]>([]);
  const [infoDialogContent, setInfoDialogContent] = useState<String>('');

  const fetchPendingUsers = useCallback(async () => {
    try {
      const rows = await apiGet<User[]>(`${getUsersURL}true`);
      setPendingUsers(rows);
      setErrorStates({ ...errorStates, getUsersError: '' });
    } catch (e: any) {
      setErrorStates({ ...errorStates, getUsersError: e.message });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiGet]);
  const fetchCurrentUsers = useCallback(async () => {
    try {
      const rows = await apiGet<User[]>(`${getUsersURL}false`);
      setCurrentUsers(transformUserData(rows));
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
      return apiDelete(ENDPOINTS.USER.replace('{user_id}', user_id)).then(
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

  const updateUser = useCallback(
    async (
      user_id: string,
      org_name: string
    ): Promise<{ success: boolean; body: string }> => {
      try {
        const res = await apiPost(
          ENDPOINTS.USER_UPDATE_V2.replace('{user_id}', user_id),
          {
            body: { invite_pending: false }
          }
        );
        apiRefPendingUsers.current?.updateRows([
          { id: user_id, _action: 'delete' }
        ]);
        setPendingUsers((prevPendingUsers) =>
          prevPendingUsers.filter((user) => user.id !== user_id)
        );
        res['organizations'] = org_name;
        apiRefCurrentUsers.current?.updateRows([res]);
        setCurrentUsers((prevCurrentUsers) => [...prevCurrentUsers, res]);
        return { success: true, body: 'User registration approved' };
      } catch (e: any) {
        setErrorStates({ ...errorStates, getUpdateError: e.message });
        return { success: false, body: e.message };
      }
    },
    [apiPost, apiRefCurrentUsers, apiRefPendingUsers, errorStates]
  );

  const addOrgToUser = useCallback(
    async (
      user_id: string,
      selectedOrgId: any
    ): Promise<{ success: boolean; body: string }> => {
      try {
        const res = await apiPost(
          ENDPOINTS.ORGANIZATION_ADD_USER.replace(
            '{organization_id}',
            selectedOrgId
          ),
          {
            body: { user_id, role: 'user' }
          }
        );
        return updateUser(user_id, res.organization.name);
      } catch (e: any) {
        setErrorStates({ ...errorStates, getUpdateError: e.message });
        return { success: false, body: e.message };
      }
    },
    [apiPost, updateUser, errorStates]
  );

  const sendApprovalEmail = useCallback(
    async (user_id: string): Promise<{ status_code: number; body: string }> => {
      try {
        const res = await apiPost(
          ENDPOINTS.USERS_REGISTER_APPROVE.replace('{user_id}', user_id),
          {}
        );
        return { status_code: res.status_code, body: res.body };
      } catch (e: any) {
        return {
          status_code: e.status_code || 500,
          body: e.message || 'Unknown error'
        };
      }
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
  };

  const handleDenyClick = (row: typeof initializeUser) => {
    setDialogStates({
      ...dialogStates,
      isDenyDialogOpen: true
    });
    selectUser(row);
  };

  const pendingCols = getPendingUserColumns({
    userType: user?.user_type,
    handleApproveClick,
    handleDenyClick
  });
  const memberCols = getMemberUserColumns();

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
      apiPost(
        ENDPOINTS.ORGANIZATION_REMOVE_ROLE.replace(
          '{organization_id}',
          org_id.toString()
        ).replace('{role_id}', roleId.toString()),
        {
          body: {}
        }
      ).then(
        (res) => {
          logger.info('RegionUsers: Organization role removed successfully', {
            response: res,
            organizationId: org_id,
            roleId
          });
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
      const emailResult = await sendApprovalEmail(selectedUser.id);
      const user_id = selectedUser.id;
      const userHadOrg = selectedUser.roles.length > 0;
      const originalOrgId = userHadOrg
        ? selectedUser.roles[0].organization.id
        : '';
      const selectedOrgId =
        selectedOrg.ids.size > 0
          ? Array.from(selectedOrg.ids)[0].toString()
          : null;
      let success = false;

      // This call is to determine if the user was already approved by another admin since opening the dialog.
      // If so, show the already approved dialog and remove the user from the pending list.
      if (
        emailResult.status_code === 200 &&
        emailResult.body === 'User registration already approved.'
      ) {
        setDialogStates((prevState) => ({
          ...prevState,
          isOrgDialogOpen: false,
          isUserAlreadyApprovedDialogOpen: true
        }));
        apiRefPendingUsers.current?.updateRows([
          { id: user_id, _action: 'delete' }
        ]);
        setPendingUsers((prevPendingUsers) =>
          prevPendingUsers.filter((user) => user.id !== user_id)
        );
        return;
      }

      // If the user's org was already added and not modified, only update the user.
      if (userHadOrg && originalOrgId === selectedOrgId) {
        const updateUserResult = await updateUser(
          selectedUser.id,
          selectedUser.roles[0].organization.name
        );
        success = updateUserResult.success;
        // If the user now has a different org than before, remove the previous org.
      } else if (userHadOrg && originalOrgId !== selectedOrgId) {
        // TODO: Make a new API endpoint to update Org for User instead of doing a removal and addition.
        removeOrgFromUser(originalOrgId, selectedUser.roles[0].id);
        const addOrgResult = await addOrgToUser(selectedUser.id, selectedOrgId);
        success = addOrgResult.success;
        // If the user had no previous org, add the user to the selected org which then also updates the user.

        // If the previous operation was successful or if the user had no previous org,
        // add the user to the selected org which then also updates the user.
      } else {
        const addOrgResult = await addOrgToUser(selectedUser.id, selectedOrgId);
        success = addOrgResult.success;
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
          Members of all regions
        </Typography>
        <Paper sx={{ height: '667px' }}>
          <DataGrid
            apiRef={apiRefCurrentUsers}
            columns={memberCols}
            rows={currentUsers}
            disableRowSelectionOnClick
            slots={{ toolbar: GridToolbar }}
            slotProps={{
              toolbar: {
                csvOptions: { disableToolbarButton: true },
                printOptions: { disableToolbarButton: true },
                showQuickFilter: false
              }
            }}
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
          <OrganizationSelector
            regionId={selectedUser.region_id}
            selectedUser={selectedUser}
            initialOrgId={selectedUser.roles[0]?.organization.id}
            onSelectionChange={(id) => {
              setSelectedOrg({
                type: 'include',
                ids: new Set(id ? [id] : [])
              });
            }}
          />
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
        icon={
          <CheckCircleOutline
            sx={{ fontSize: '80px', color: theme.palette.primary.dark }}
          />
        }
        title={<Typography variant="h4">Success </Typography>}
        content={<Typography variant="body1">{infoDialogContent}</Typography>}
      />
      <AlreadyApprovedDialog
        isOpen={dialogStates.isUserAlreadyApprovedDialogOpen}
        handleClick={() =>
          setDialogStates((prevState) => ({
            ...prevState,
            isUserAlreadyApprovedDialogOpen: false
          }))
        }
        icon={<InfoOutline color="info" sx={{ fontSize: '80px' }} />}
        title={<Typography variant="h4">User already approved</Typography>}
        content={
          <Typography variant="body1">
            This user was previously approved by another administrator.
            <br />
            Check the approval history in Admin Tools → User Logs for more
            details.
          </Typography>
        }
      />
    </Box>
  );
};

export default RegionUsers;
