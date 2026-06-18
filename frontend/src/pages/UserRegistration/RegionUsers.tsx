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

/** Refresh pending/member tables while admins work on this page (ms). */
const REGISTRATION_USERS_REFRESH_INTERVAL_MS = 30_000;

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
  const [selectedOrgObject, setSelectedOrgObject] = useState<any>(null);
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [currentUsers, setCurrentUsers] = useState<User[]>([]);
  const [infoDialogContent, setInfoDialogContent] = useState<String>('');

  const fetchPendingUsers = useCallback(async () => {
    try {
      const rows = await apiGet<User[]>(`${getUsersURL}true`);
      setPendingUsers(rows);
      setErrorStates((prev) => ({ ...prev, getUsersError: '' }));
    } catch (e: any) {
      setErrorStates((prev) => ({ ...prev, getUsersError: e.message }));
    }
  }, [apiGet, getUsersURL]);
  const fetchCurrentUsers = useCallback(async () => {
    try {
      const rows = await apiGet<User[]>(`${getUsersURL}false`);
      setCurrentUsers(transformUserData(rows));
      setErrorStates((prev) => ({ ...prev, getUsersError: '' }));
    } catch (e: any) {
      setErrorStates((prev) => ({ ...prev, getUsersError: e.message }));
    }
  }, [apiGet, getUsersURL]);

  const isRegistrationDialogOpen =
    dialogStates.isOrgDialogOpen ||
    dialogStates.isDenyDialogOpen ||
    dialogStates.isInfoDialogOpen ||
    dialogStates.isUserAlreadyApprovedDialogOpen;

  useEffect(() => {
    fetchPendingUsers();
    fetchCurrentUsers();
  }, [fetchPendingUsers, fetchCurrentUsers]);

  // Keep registration tables in sync with the server. Polling is paused while a
  // dialog is open (so approve/deny flows are not disrupted) and while the tab
  // is hidden. Does not reset session inactivity — that only tracks mouse/keyboard.
  useEffect(() => {
    const refreshRegistrationTables = () => {
      if (document.hidden || isRegistrationDialogOpen) {
        return;
      }
      fetchPendingUsers();
      fetchCurrentUsers();
    };

    const intervalId = window.setInterval(
      refreshRegistrationTables,
      REGISTRATION_USERS_REFRESH_INTERVAL_MS
    );

    const onVisibilityChange = () => {
      if (!document.hidden) {
        refreshRegistrationTables();
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [fetchPendingUsers, fetchCurrentUsers, isRegistrationDialogOpen]);

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
      selectedOrgObject: any
    ): Promise<{ success: boolean; body: string }> => {
      try {
        const res = await apiPost(
          ENDPOINTS.USER_UPDATE_V2.replace('{user_id}', user_id),
          {
            body: { invite_pending: false }
          }
        );
        const mockRoles = [
          {
            organization: {
              id: selectedOrgObject.id,
              name: selectedOrgObject.name,
              acronym: selectedOrgObject.acronym
            }
          }
        ];
        // Combine the API response with selection data
        const updatedUserWithRoles = { ...res, roles: mockRoles };
        const transformedUser = transformUserData([updatedUserWithRoles])[0];
        apiRefPendingUsers.current?.updateRows([
          { id: user_id, _action: 'delete' }
        ]);
        setPendingUsers((prev) => prev.filter((u) => u.id !== user_id));
        apiRefCurrentUsers.current?.updateRows([transformedUser]);
        setCurrentUsers((prev) => [...prev, transformedUser]);
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
      orgObject: any
    ): Promise<{ success: boolean; body: string }> => {
      try {
        await apiPost(
          ENDPOINTS.ORGANIZATION_ADD_USER.replace(
            '{organization_id}',
            orgObject.id // Extract ID for the API call
          ),
          { body: { user_id, role: 'user' } }
        );
        return updateUser(user_id, orgObject);
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
    setSelectedOrgObject(null);
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
    setSelectedOrgObject(null);
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
    setSelectedOrgObject(null);
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
      const userHadOrg = selectedUser.roles.length > 0;
      const originalOrgId = userHadOrg
        ? selectedUser.roles[0].organization.id
        : '';
      const selectedOrgId = selectedOrgObject?.id || null;
      let success = false;

      // User was approved earlier (e.g. register/approve succeeded but invite_pending was
      // never cleared). Finish approval by assigning org if needed, then clear pending.
      if (
        emailResult.status_code === 200 &&
        emailResult.body === 'User registration already approved.'
      ) {
        let alreadyApprovedSuccess = false;

        if (userHadOrg && originalOrgId === selectedOrgId) {
          const updateUserResult = await updateUser(
            selectedUser.id,
            selectedUser.roles[0].organization
          );
          alreadyApprovedSuccess = updateUserResult.success;
        } else if (selectedOrgObject) {
          const addOrgResult = await addOrgToUser(
            selectedUser.id,
            selectedOrgObject
          );
          alreadyApprovedSuccess = addOrgResult.success;
        } else if (selectedUser.roles[0]?.organization) {
          const updateUserResult = await updateUser(
            selectedUser.id,
            selectedUser.roles[0].organization
          );
          alreadyApprovedSuccess = updateUserResult.success;
        }

        if (alreadyApprovedSuccess) {
          const approvedOrgName =
            selectedOrgObject?.name ??
            selectedUser.roles[0]?.organization?.name ??
            'the selected organization';
          handleCloseDialog('closeButtonClick');
          setDialogStates((prevState) => ({
            ...prevState,
            isInfoDialogOpen: true
          }));
          setInfoDialogContent(
            `This user was previously approved. Their registration is now complete and they are a member of ${approvedOrgName} in Region ${selectedUser.region_id}.`
          );
        } else {
          setDialogStates((prevState) => ({
            ...prevState,
            isOrgDialogOpen: false,
            isUserAlreadyApprovedDialogOpen: true
          }));
        }
        return;
      }

      // If the user's org was already added and not modified, only update the user.
      if (userHadOrg && originalOrgId === selectedOrgId) {
        const existingOrg = selectedUser.roles[0].organization;
        const updateUserResult = await updateUser(selectedUser.id, existingOrg);
        success = updateUserResult.success;
      } else if (userHadOrg && originalOrgId !== selectedOrgId) {
        // TODO: Make a new API endpoint to update Org for User instead of doing a removal and addition.
        removeOrgFromUser(originalOrgId, selectedUser.roles[0].id);
        // Pass the full selected object to both
        const addOrgResult = await addOrgToUser(
          selectedUser.id,
          selectedOrgObject
        );
        success = addOrgResult.success;
      } else {
        // Pass the full selected object
        const addOrgResult = await addOrgToUser(
          selectedUser.id,
          selectedOrgObject
        );
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

  const handleOrgSelectionChange = useCallback((org: any) => {
    setSelectedOrg({
      type: 'include',
      ids: new Set(org ? [org.id] : [])
    });
    setSelectedOrgObject(org);
  }, []);

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
            onSelectionChange={handleOrgSelectionChange}
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
