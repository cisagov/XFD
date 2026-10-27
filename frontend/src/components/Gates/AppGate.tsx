import React from 'react';
import { BoxProps } from '@mui/material/Box';
// Context & hooks
import { useAuthContext } from 'context';
import { useCheckUserState } from 'hooks/useCheckUserState';
import { useMaintenanceNotifications } from '@/hooks/useMaintenanceNotifications';

// Shared components
import { LoginBlockedDialog } from 'components/LoginBlockedDialog';
import { UpdateStateForm } from '@/components/UpdateUserStateForm';
import InvitePendingCard from 'components/Dialog/InvitePendingCard';
import { ENDPOINTS } from '@/constants/endpoints';

export interface VulnSeverities {
  label: string;
  sevList: string[];
  disable?: boolean;
  amount?: number;
}

export interface WidgetProps extends BoxProps {
  children?: React.ReactNode;
}

type notifications = {
  status: string;
  maintenance_type: string;
  start_datetime: string;
  end_datetime: string;
  message: string;
};

type updatedUser = {
  state: string;
  user_type: string;
};

const AppGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, apiGet, userMustSign, logout, isLoggingOut } = useAuthContext();

  const { isUpdateStateFormOpen, setIsUpdateStateFormOpen } = useCheckUserState(
    user,
    isLoggingOut
  );
  const {
    isLoginBlockedDialogOpen,
    setIsLoginBlockedDialogOpen,
    maintenanceNotification,
    setMaintenanceNotification
  } = useMaintenanceNotifications(user, apiGet, userMustSign);

  if (isUpdateStateFormOpen) {
    return (
      <UpdateStateForm
        open={isUpdateStateFormOpen}
        user_id={user?.id ?? ''}
        onClose={async () => {
          setIsUpdateStateFormOpen(false);
          const updatedUser = await apiGet<updatedUser>('/users/me');
          if (updatedUser?.state && user?.user_type !== 'globalAdmin') {
            const notifications = await apiGet<notifications[]>(
              ENDPOINTS.NOTIFICATIONS
            );
            const active = notifications.find(
              (n: notifications) =>
                n.status === 'active' &&
                n.maintenance_type === 'major' &&
                new Date(n.start_datetime) <= new Date() &&
                new Date(n.end_datetime) >= new Date()
            );
            if (active && updatedUser.user_type !== 'globalAdmin') {
              setMaintenanceNotification(active);
              setIsLoginBlockedDialogOpen(true);
            }
          }
        }}
      />
    );
  }
  if (isLoginBlockedDialogOpen && maintenanceNotification) {
    return (
      <LoginBlockedDialog
        open={isLoginBlockedDialogOpen}
        message={maintenanceNotification.message}
        onClose={() => {
          setIsLoginBlockedDialogOpen(false);
          logout();
        }}
      />
    );
  }
  if (user?.invite_pending) {
    return <InvitePendingCard />;
  }

  return <>{children}</>;
};

export default AppGate;
