import React from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';

type DialogComponentProps = {
  isOpen: boolean;
  onClose?: (...args: any[]) => void;
  onConfirm: () => void;
  onCancel: () => void;
  onSave?: () => void;
  title: string;
  content: React.ReactNode;
  disabled?: boolean;
  screenWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
};

const ConfirmDialog: React.FC<DialogComponentProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onCancel,
  onSave,
  title,
  content,
  disabled = false,
  screenWidth = 'sm'
}) => {
  return (
    <Dialog open={isOpen} onClose={onClose} fullWidth maxWidth={screenWidth}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>{content}</DialogContent>
      <DialogActions sx={{ pb: 3, pr: 3 }}>
        <Button size="large" variant="text" onClick={onCancel}>
          Cancel
        </Button>
        {onSave && (
          <Button
            size="large"
            variant="outlined"
            onClick={onSave}
            disabled={disabled}
          >
            Save
          </Button>
        )}
        <Button
          size="large"
          variant="contained"
          onClick={onConfirm}
          disabled={disabled}
        >
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConfirmDialog;
