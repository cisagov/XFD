import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import { useSavedSearchContext } from 'context/SavedSearchContext';
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
import { SavedSearch } from '../../types/saved-search';
import { useAuthContext } from '../../context';
import { Save } from '@mui/icons-material';

interface SaveSearchModalProps {
  search: any;
  searchTerm: string;
  filters: any;
  totalResults: number;
  sortField: string;
  sortDirection: string;
  advancedFiltersReq?: boolean;
}

export const SaveSearchModal: React.FC<SaveSearchModalProps> = (props) => {
  const {
    search,
    searchTerm,
    filters,
    totalResults,
    sortField,
    sortDirection,
    advancedFiltersReq
  } = props;
  const [open, setOpen] = useState(false);
  const [dialogeOpen, setDialogOpen] = useState(false);
  const [formErrors, setFormErrors] = useState({
    name: false,
    duplicate: false
  });
  const { apiGet, apiPost, apiPut } = useAuthContext();
  const { savedSearches, setSavedSearches, setSavedSearchCount } =
    useSavedSearchContext();
  const [savedSearchValues, setSavedSearchValues] = useState<
    Partial<SavedSearch> & { name: string }
  >(search ? search : { name: '' });

  // API call to save/update saved searches
  const handleSave = async (savedSearchValues: Partial<SavedSearch>) => {
    const body = {
      body: {
        ...savedSearchValues,
        searchTerm,
        filters,
        count: totalResults,
        searchPath: window.location.search,
        sortField,
        sortDirection
      }
    };

    try {
      if (search) {
        await apiPut('/saved-searches/' + search.id, body);
      } else {
        await apiPost('/saved-searches/', body);
      }
      const updatedSearches = await apiGet('/saved-searches'); // Get current saved searches
      setSavedSearches(updatedSearches.result); // Update the saved searches
      setSavedSearchCount(updatedSearches.result.length); // Update the count
      localStorage.removeItem('savedSearch');
    } catch (e) {
      console.error(e);
    }
  };

  const handleCloseModal = () => {
    setOpen(false);
  };
  const handleOpenModal = () => {
    setOpen(true);
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
  };

  const handleClick = () => {
    if (search) {
      savedSearchValues.name = search.name;
      setDialogOpen(true); // Open dialog to confirm update
    } else {
      handleOpenModal();
    }
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (formErrors.name) {
      return;
    }
    handleSave(savedSearchValues);
    handleCloseModal();
  };

  // Validate Saved Search Name
  const validation = (name: string): boolean => {
    const nameRegex = /^(?=.*[A-Za-z0-9])[A-Za-z0-9\s'-]+$/;
    return nameRegex.test(name);
  };

  const handleChange = (name: string, value: any) => {
    setSavedSearchValues((values) => ({
      ...values,
      [name]: value
    }));
    // Validation check for valid characters and duplicate names
    if (name === 'name') {
      const isValid = validation(value);
      const isDuplicate = savedSearches.some((search) => search.name === value);

      setFormErrors((prev) => ({
        ...prev,
        name: !isValid,
        duplicate: isDuplicate
      }));
    }
  };

  return (
    <>
      <Button
        variant="contained"
        onClick={handleClick}
        endIcon={<Save />}
        disabled={!advancedFiltersReq}
        aria-label={search ? 'Update Saved Search' : 'Save Search'}
      >
        {search ? 'Update Saved Search' : 'Save Search'}
      </Button>
      <Dialog
        open={dialogeOpen}
        onClose={() => setDialogOpen(false)}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <DialogTitle id="confirm-dialog-title">Update Saved Search</DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-dialog-description">
            Are you sure you want to update this saved search?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose} color="primary">
            No
          </Button>
          <Button
            variant="contained"
            onClick={() => {
              try {
                handleSave(savedSearchValues);
                setDialogOpen(false);
              } catch (e) {
                console.error(e);
              }
            }}
            color="primary"
            autoFocus
          >
            Yes
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={open}
        onClose={handleCloseModal}
        PaperProps={{
          component: 'form',
          onSubmit: handleSubmit,
          style: { width: '30%', minWidth: '300px' }
        }}
        aria-labelledby="dialog-title"
        aria-describedby="dialog-description"
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
              name="name"
              placeholder="Enter a name"
              type="text"
              fullWidth
              variant="outlined"
              value={savedSearchValues.name}
              onChange={(e) => handleChange(e.target.name, e.target.value)}
              inputProps={{
                'aria-label': 'Enter a name for your saved search'
              }}
              error={formErrors.name}
              helperText={
                formErrors.name
                  ? 'Name is required and must contain only alphanumeric characters, spaces, hyphens, or apostrophes.'
                  : formErrors.duplicate
                  ? 'This name is already taken. Please choose a different name.'
                  : ''
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal}>Cancel</Button>
          <Button
            variant="contained"
            type="submit"
            disabled={
              formErrors.name ||
              formErrors.duplicate ||
              !savedSearchValues.name.trim()
            }
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
