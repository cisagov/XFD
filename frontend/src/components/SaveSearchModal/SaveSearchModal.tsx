import React, { useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
  Button,
  Box
} from '@mui/material/';
import { SavedSearch } from 'types';

interface SaveSearchModalProps {
  open: boolean;
  handleSave: (FormData: Partial<SavedSearch>) => void; //TODO
  handleClose: () => void;
  savedSearchValues: Partial<SavedSearch>; //TODO
  setSavedSearchValues: React.Dispatch<
    React.SetStateAction<Partial<SavedSearch>>
  >; //TODO
}

export default function SaveSearchModal({
  open,
  handleClose,
  handleSave,
  savedSearchValues,
  setSavedSearchValues
}: SaveSearchModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open && dialogRef.current) {
      dialogRef.current.focus();
    }
  }, [open]);

  // TODO
  const handleCloseModal = () => {
    console.log('closing modal: ', dialogRef);
    handleClose();
    // TODO: Focus on the trigger button when the modal closes
    // if (triggerButtonRef.current) {
    //   triggerButtonRef.current.focus();
    // }
  };

  // TODO
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSavedSearchValues((prevValues) => ({
      ...prevValues,
      [name]: value
    }));
  };
  // TODO
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    handleSave(savedSearchValues);
    handleClose();
  };

  return (
    <>
      {/* <Button ref={triggerButtonRef} onClick={() => open = true}>Open Modal</Button> */}
      <Dialog
        open={open}
        onClose={handleCloseModal}
        PaperProps={{
          component: 'form',
          onSubmit: handleSubmit,
          // (event: React.FormEvent<HTMLFormElement>) => {
          //   event.preventDefault();
          //   const formData = new FormData(event.currentTarget);
          //   const formJson = Object.fromEntries((formData as any).entries());
          //   const savedSearch = formJson;
          //   console.log(savedSearch);
          //   handleCloseModal();
          // }
          style: { width: '30%', minWidth: '300px' }
        }}
        aria-labelledby="dialog-title"
        aria-describedby="dialog-description"
        ref={dialogRef}
      >
        <DialogTitle id="dialog-title">Save Search</DialogTitle>
        <DialogContent>
          <Box paddingBottom={'1em'}>
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
              value={savedSearchValues.name}
              onChange={handleChange}
              inputProps={{
                'aria-label': 'Enter a name for your saved search'
              }}
            />
          </Box>
          {/* TODO:
              Not sure if necessary at this point
          */}
          {/* <DialogContentText id="checkbox-description">
            When a result is found:
          </DialogContentText>

          <Box display="flex" alignItems="center">
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
