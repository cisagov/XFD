import React from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography
} from '@mui/material';

// TODO: Determine if custom styled Dialog exists. This uses MUI's built-in Dialog.
const StyledDialog = Dialog;

export interface LoginBlockedDialogProps {
  open: boolean;
  onClose: () => void;
  message: string;
}

export const LoginBlockedDialog: React.FC<LoginBlockedDialogProps> = ({
  open,
  onClose,
  message
}) => {
  return (
    <StyledDialog
      open={open}
      onClose={(
        event: object,
        reason: 'backdropClick' | 'escapeKeyDown' | 'closeButtonClick'
      ) => {
        if (reason !== 'backdropClick' && reason !== 'escapeKeyDown') {
          onClose();
        }
      }}
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle id="login-blocked-dialog-title">
        CyHy Dashboard Unavailable Due to Maintenance
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" sx={{ mt: 1 }}>
          {message ||
            'The system is undergoing maintenance. Please check back later.'}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained" color="primary">
          Logout
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};
