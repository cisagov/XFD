import React, { useId } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';

type DialogComponentProps = {
  isOpen: boolean;
  onClose?: (...args: any[]) => void;
  onConfirm?: () => void;
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
  const titleId = useId();
  const contentId = useId();
  return (
    <Dialog
      open={isOpen}
      onClose={onClose ?? onCancel}
      fullWidth
      maxWidth={screenWidth}
      aria-labelledby={`dialog-title-${titleId}`}
    >
      <DialogTitle id={`dialog-title-${titleId}`}>{title}</DialogTitle>
      <DialogContent id={`dialog-content-${contentId}`}>
        {content}
      </DialogContent>
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
        {onConfirm && (
          <Button
            size="large"
            variant="contained"
            onClick={onConfirm}
            disabled={disabled}
          >
            Confirm
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ConfirmDialog;
