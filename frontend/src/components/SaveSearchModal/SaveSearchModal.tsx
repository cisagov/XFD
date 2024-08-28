import React, { useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
  Button,
  Box,
  Checkbox
} from '@mui/material/';

interface SaveSearchModalProps {
  open: boolean;
  handleClose: () => void;
}

export default function SaveSearchModal({
  open,
  handleClose
}: SaveSearchModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open && dialogRef.current) {
      dialogRef.current.focus();
    }
  }, [open]);

  const [checked, setChecked] = useState(false);

  const handleCheck = (event: React.ChangeEvent<HTMLInputElement>) => {
    setChecked(event.target.checked);
  };

  const handleCloseModal = () => {
    handleClose();
    // TODO: Focus on the trigger button when the modal closes
    // if (triggerButtonRef.current) {
    //   triggerButtonRef.current.focus();
    // }
  };

  useEffect(() => {
    if (!open) {
      setChecked(false);
    }
  }, [open, setChecked]);

  return (
    <>
      {/* <Button ref={triggerButtonRef} onClick={() => open = true}>Open Modal</Button> */}
      <Dialog
        open={open}
        onClose={handleCloseModal}
        PaperProps={{
          component: 'form',
          onSubmit: (event: React.FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            const formJson = Object.fromEntries((formData as any).entries());
            const savedSearch = formJson;
            console.log(savedSearch);
            handleCloseModal();
          },
          style: { width: '30%', minWidth: '300px' }
        }}
        aria-labelledby="dialog-title"
        aria-describedby="dialog-description"
        ref={dialogRef}
      >
        <DialogTitle id="dialog-title">Save Search</DialogTitle>
        <DialogContent>
          <Box paddingBottom={'2em'}>
            <DialogContentText id="dialog-description">
              Name Your Search
            </DialogContentText>
            <TextField
              autoFocus
              required
              margin="dense"
              id="name"
              name="savedSearch"
              placeholder="Enter a name"
              type="text"
              fullWidth
              variant="outlined"
              inputProps={{
                'aria-label': 'Enter a name for your saved search'
              }}
            />
          </Box>
          {/* <DialogContentText id="checkbox-description">
            When a result is found:
          </DialogContentText> */}
          {/* TODO:
              Not sure of functionality at this point
          */}
          {/* <Box display="flex" alignItems="center">
              <Checkbox
                id="create-vulnerability-checkbox"
                name='createVulnerability'
                checked={checked}
                onChange={handleCheck}
                inputProps={{
                  'aria-label': 'controlled'
                }}
              />
              <label htmlFor="create-vulnerability-checkbox" style={{ marginLeft: '0.2em' }}>
                Create a Vulnerability
              </label>
            </Box> */}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal}>Cancel</Button>
          <Button type="submit">Save</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
