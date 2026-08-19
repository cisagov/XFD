import React, { useState, useEffect, useCallback } from 'react';

// Material-UI Components
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutline';
import InfoOutline from '@mui/icons-material/InfoOutline';

// DataGrid Components
import {
  GridRowSelectionModel,
  GridToolbar,
  useGridApiRef
} from '@mui/x-data-grid';

// Components
import AlreadyApprovedDialog from 'components/Dialog/AlreadyApprovedDialog';
import ConfirmDialog from 'components/Dialog/ConfirmDialog';
import CustomDataGrid from '@/components/DataGrid/CustomDataGrid';
import { ExportCustomerMetricsButton } from '@components/Metrics/Widgets/ExportCustomerMetricsButton';
import InfoDialog from 'components/Dialog/InfoDialog';
import { OrganizationSelector } from './OrganizationSelector';

// Constants
import { initializeUser } from '@/constants/userAndOrgData';
import { ENDPOINTS } from '@/constants/endpoints';

// Context
import { useAuthContext } from 'context';
import { useTheme } from '@mui/material/styles';

// Hooks
import {
  getPendingUserColumns,
  getMemberUserColumns
} from './UserRegistrationColumns';
import { useUserLevel } from 'hooks/useUserLevel';

// Types
import { User } from 'types';

// Utils
import { logger } from '@/utils/logger';
import { transformUserData } from '@/utils/transformTableData';

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
const INITIAL_ERROR_STATES: ErrorStates = {
  getUsersError: '',
  getUpdateError: '',
  getDeleteError: ''
};

export const RegionUsers: React.FC = () => {
  const { apiDelete, apiGet, apiPost, user: loggedInUser } = useAuthContext();
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
  const [errorStates, setErrorStates] =
    useState<ErrorStates>(INITIAL_ERROR_STATES);
  const [selectedUser, selectUser] = useState<User>(initializeUser);
  const [selectedOrg, setSelectedOrg] = React.useState<GridRowSelectionModel>({
    type: 'include',
    ids: new Set<string | number>()
  });
  const [selectedOrgObject, setSelectedOrgObject] = useState<any>(null);
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [currentUsers, setCurrentUsers] = useState<User[]>([]);
  const [infoDialogContent, setInfoDialogContent] = useState<String>('');
  const [isRoleElevationConfirmed, setIsRoleElevationConfirmed] =
    useState(false);
  const [confirmGlobalAdminChange, setConfirmGlobalAdminChange] = useState('');
  const isNewGlobalAdmin =
    pendingUsers?.find((userItem: User) => userItem.id === selectedUser.id)
      ?.user_type !== selectedUser.user_type &&
    selectedUser.user_type === 'globalAdmin';
  const isNewRegionalOrGlobalView =
    pendingUsers?.find((userItem: User) => userItem.id === selectedUser.id)
      ?.user_type !== selectedUser.user_type &&
    (selectedUser.user_type === 'regionalAdmin' ||
      selectedUser.user_type === 'globalView');

  const fetchPendingUsers = useCallback(async () => {
    try {
      const rows = await apiGet<User[]>(`${getUsersURL}true`);
      setPendingUsers(rows);
      setErrorStates((prev) => ({ ...prev, getUsersError: '' }));
      return rows;
    } catch (e: any) {
      setErrorStates((prev) => ({ ...prev, getUsersError: e.message }));
      throw e;
    }
  }, [apiGet, getUsersURL]);

  const fetchCurrentUsers = useCallback(async () => {
    try {
      const rows = await apiGet<User[]>(`${getUsersURL}false`);
      setCurrentUsers(transformUserData(rows));
      setErrorStates((prev) => ({ ...prev, getUsersError: '' }));
      return rows;
    } catch (e: any) {
      setErrorStates((prev) => ({ ...prev, getUsersError: e.message }));
      throw e;
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
    async (user_id: string): Promise<boolean> => {
      return apiDelete(ENDPOINTS.USER.replace('{user_id}', user_id)).then(
        async () => {
          await fetchPendingUsers();
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
      selectedUser: User,
      isSaveAction: boolean
    ): Promise<{ success: boolean; body: string }> => {
      try {
        await apiPost(
          ENDPOINTS.USER_UPDATE_V2.replace('{user_id}', selectedUser.id),
          {
            body: {
              invite_pending: isSaveAction,
              state: selectedUser.state,
              ...(loggedInUser?.user_type === 'globalAdmin' && {
                user_type: selectedUser.user_type
              })
            },
            headers: { 'X-Origin-Path': 'user-registration' }
          }
        );

        await fetchPendingUsers();
        if (!isSaveAction) {
          await fetchCurrentUsers();
        }

        return { success: true, body: 'Pending User Updated' };
      } catch (e: any) {
        setErrorStates({ ...errorStates, getUpdateError: e.message });
        return { success: false, body: e.message };
      }
    },
    [
      apiPost,
      fetchPendingUsers,
      fetchCurrentUsers,
      errorStates,
      loggedInUser?.user_type
    ]
  );

  const addOrgToUser = useCallback(
    async (
      selectedUser: User,
      orgObject: any,
      isSaveAction: boolean
    ): Promise<{ success: boolean; body: string }> => {
      try {
        await apiPost(
          ENDPOINTS.ORGANIZATION_ADD_USER.replace(
            '{organization_id}',
            orgObject.id // Extract ID for the API call
          ),
          { body: { user_id: selectedUser.id, role: 'user' } }
        );
        return updateUser(selectedUser, isSaveAction);
      } catch (e: any) {
        setErrorStates({ ...errorStates, getUpdateError: e.message });
        return { success: false, body: e.message };
      }
    },
    [apiPost, updateUser, errorStates]
  );

  const completeRegistrationApproval = useCallback(
    async (
      selectedUser: User,
      organizationId: string
    ): Promise<{
      status_code: number;
      body: string;
      already_approved?: boolean;
      email_sent?: boolean;
    }> => {
      try {
        const res = await apiPost(
          ENDPOINTS.USERS_REGISTER_APPROVE.replace(
            '{user_id}',
            selectedUser.id
          ),
          {
            body: {
              state: selectedUser.state,
              organization_id: organizationId,
              ...(loggedInUser?.user_type === 'globalAdmin' && {
                user_type: selectedUser.user_type
              })
            }
          }
        );
        return {
          status_code: res.status_code,
          body: res.body,
          already_approved: res.already_approved,
          email_sent: res.email_sent
        };
      } catch (e: any) {
        return {
          status_code: e.statusCode || e.status_code || 500,
          body:
            e.body?.detail ||
            e.response?.data?.detail ||
            e.detail ||
            e.message ||
            'Unknown error',
          already_approved: undefined,
          email_sent: undefined
        };
      }
    }, // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiPost, loggedInUser?.user_type]
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
    setErrorStates((prevState) => ({
      ...prevState,
      getUpdateError: ''
    }));
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
    userType: loggedInUser?.user_type,
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
    setErrorStates(INITIAL_ERROR_STATES);
  };

  const removeOrgFromUser = useCallback(
    (org_id: String | undefined | null, roleId: String | undefined | null) => {
      // Fail if parameters are completely missing
      if (!org_id || !roleId) {
        logger.warn('RegionUsers: Missing org_id or roleId for removal bypass');
        return Promise.resolve();
      }
      return apiPost(
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
          throw e;
        }
      );
    }, // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiPost]
  );

  const handleApproveConfirmClick = async (isSaveAction = false) => {
    try {
      // Check if roles and ids exist
      const userHadOrg = (selectedUser?.roles?.length ?? 0) > 0;
      const originalOrgId = selectedUser?.roles?.[0]?.organization?.id || '';
      const originalRoleId = selectedUser?.roles?.[0]?.id || '';
      const selectedOrgId = selectedOrgObject?.id || null;
      let success = false;
      let alreadyApproved = false;
      let emailSent: boolean | undefined;
      if (!isSaveAction) {
        if (!selectedOrgId) {
          throw new Error('Select an organization before approving the user.');
        }
        const approvalResult = await completeRegistrationApproval(
          selectedUser,
          selectedOrgId
        );
        success = approvalResult.status_code === 200;
        alreadyApproved = approvalResult.already_approved === true;
        emailSent = approvalResult.email_sent;
        if (success) {
          await fetchPendingUsers();
          await fetchCurrentUsers();
        } else {
          throw new Error(approvalResult.body || 'Unable to approve the user.');
        }
      } else if (userHadOrg && originalOrgId === selectedOrgId) {
        const updateUserResult = await updateUser(selectedUser, isSaveAction);
        success = updateUserResult.success;
      } else if (userHadOrg && originalOrgId !== selectedOrgId) {
        // TODO: Make a new API endpoint to update Org for User instead of doing a removal and addition.
        if (originalOrgId && originalRoleId) {
          await removeOrgFromUser(originalOrgId, originalRoleId);
        }
        // Pass the full selected object to both
        const addOrgResult = await addOrgToUser(
          selectedUser,
          selectedOrgObject,
          isSaveAction
        );
        success = addOrgResult.success;
      } else {
        // Pass the full selected object
        const addOrgResult = await addOrgToUser(
          selectedUser,
          selectedOrgObject,
          isSaveAction
        );
        success = addOrgResult.success;
      }
      if (success) {
        setPendingUsers((freshPendingList) => {
          const updatedProfile = freshPendingList.find(
            (u) => u.id === selectedUser.id
          );
          if (updatedProfile) {
            selectUser(updatedProfile);
          }
          return freshPendingList;
        });
        handleCloseDialog('closeButtonClick');
        setDialogStates((prevState) => ({
          ...prevState,
          isInfoDialogOpen: true
        }));
        setInfoDialogContent(
          isSaveAction
            ? 'The user has been saved.'
            : alreadyApproved
              ? 'This user was already approved.'
              : `The user has been approved and is a member of Region ${selectedUser.region_id}. ${emailSent === false ? 'The approval email could not be sent. Check the network tab for details.' : 'The approval email was sent.'}`
        );
      } else {
        setErrorStates({
          ...errorStates,
          getUpdateError: 'Failed to update the user.'
        });
        throw new Error('Failed to update the user.');
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
          <CustomDataGrid
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
          <CustomDataGrid
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
        onConfirm={() => handleApproveConfirmClick(false)}
        onSave={() => handleApproveConfirmClick(true)}
        onCancel={handleApproveCancelClick}
        title={`Add ${selectedUser.full_name} to an organization in Region ${selectedUser.region_id}`}
        content={
          <OrganizationSelector
            pendingUsers={pendingUsers}
            regionId={selectedUser.region_id}
            selectedUser={selectedUser}
            selectUser={selectUser}
            formattedUserType={formattedUserType}
            initialOrgId={selectedUser.roles[0]?.organization.id}
            onSelectionChange={handleOrgSelectionChange}
            getUpdateError={errorStates.getUpdateError}
            isRoleElevationConfirmed={isRoleElevationConfirmed}
            setIsRoleElevationConfirmed={setIsRoleElevationConfirmed}
            confirmGlobalAdminChange={confirmGlobalAdminChange}
            setConfirmGlobalAdminChange={setConfirmGlobalAdminChange}
          />
        }
        disabled={
          selectedOrg.ids.size === 0 ||
          (isNewGlobalAdmin &&
            confirmGlobalAdminChange !== 'Global Administrator') ||
          (isNewRegionalOrGlobalView && !isRoleElevationConfirmed)
        }
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
