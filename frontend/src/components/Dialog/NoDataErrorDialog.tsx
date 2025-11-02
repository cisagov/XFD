import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  Typography,
  IconButton,
  Box
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

export interface NoDataErrorDialogProps {
  open?: boolean;
  message?: string;
  onClose?: () => void;
}

const defaultMessage = `No matching data available.\nPlease refine filters and retry the search.`;

const NoDataErrorDialog: React.FC<NoDataErrorDialogProps> = ({
  open = true,
  message = defaultMessage,
  onClose
}) => {
  const [internalOpen, setInternalOpen] = useState(open);

  const handleClose = () => {
    if (onClose) {
      onClose();
    } else {
      setInternalOpen(false);
    }
  };

  return (
    <Dialog
      open={internalOpen}
      onClose={handleClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: { sx: { textAlign: 'center', padding: '2rem', borderRadius: 2 } }
      }}
    >
      <IconButton
        onClick={handleClose}
        sx={{ position: 'absolute', top: 8, right: 8 }}
        aria-label="Close dialog"
      >
        <CloseIcon />
      </IconButton>

      <DialogContent>
        <Box display="flex" flexDirection="column" alignItems="center">
          <ErrorOutlineIcon
            color="primary"
            sx={{ fontSize: 40, marginBottom: 2 }}
          />
          {message.split('\n').map((line, idx) => (
            <Typography
              key={idx}
              variant="body1"
              sx={{ mb: idx === 0 ? 1 : 0 }}
            >
              {line}
            </Typography>
          ))}
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default NoDataErrorDialog;
