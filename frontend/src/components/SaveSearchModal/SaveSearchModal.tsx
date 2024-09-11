import React, { useState } from 'react';
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
  searchTerm: string;
  filters: any;
  totalResults: number;
  sortField: string;
  sortDirection: string;
  advancedFiltersReq?: boolean;
}

export const SaveSearchModal: React.FC<SaveSearchModalProps> = (props) => {
  const {
    searchTerm,
    filters,
    totalResults,
    sortField,
    sortDirection,
    advancedFiltersReq
  } = props;
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const [formErrors, setFormErrors] = useState({
    name: false,
    duplicate: false
  });
  const { apiGet, apiPost, apiPut } = useAuthContext();
  const { savedSearches, setSavedSearches, setSavedSearchCount, activeSearch } =
    useSavedSearchContext();
  const [savedSearchValues, setSavedSearchValues] = useState<
    Partial<SavedSearch> & { name: string }
  >(activeSearch ? activeSearch : { name: '' });
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
      if (activeSearch) {
        await apiPut('/saved-searches/' + activeSearch.id, body);
      } else {
        await apiPost('/saved-searches/', body);
      }
      const updatedSearches = await apiGet('/saved-searches'); // Get current saved searches
      setSavedSearches(updatedSearches.result); // Update the saved searches
      setSavedSearchCount(updatedSearches.result.length); // Update the count
    } catch (e) {
      console.error(e);
    }
  };

  const handleCloseModal = () => {
    setSaveDialogOpen(false);
    savedSearchValues.name = '';
  };
  const handleOpenModal = () => {
    setSaveDialogOpen(true);
  };

  const handleDialogClose = () => {
    setUpdateDialogOpen(false);
    savedSearchValues.name = '';
  };

  const handleUpdate = () => {
    if (activeSearch) {
      savedSearchValues.name = activeSearch.name;
      setUpdateDialogOpen(true); // Open dialog to confirm update
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

  const handleChange = (textInputName: string, textInput: string) => {
    setSavedSearchValues((inputValues) => ({
      ...inputValues,
      [textInputName]: textInput
    }));
    // Validation check for valid characters and duplicate names
    if (textInputName === 'name' && textInput !== activeSearch?.name) {
      const isValid = validation(textInput);
      const isDuplicate = savedSearches.some(
        (search) => search.name === textInput
      );

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
        tabIndex={0}
        variant="contained"
        onClick={handleUpdate}
        endIcon={<Save />}
        disabled={!advancedFiltersReq}
        aria-label={activeSearch ? 'Update Saved Search' : 'Save Search'}
      >
        {activeSearch ? 'Update Saved Search' : 'Save Search'}
      </Button>
      <Dialog
        open={updateDialogOpen}
        onClose={() => setUpdateDialogOpen(false)}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        PaperProps={{
          component: 'form',
          onSubmit: handleSubmit,
          style: { width: '30%', minWidth: '300px' }
        }}
      >
        <DialogTitle id="confirm-dialog-title">Update Saved Search</DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-dialog-description">
            <TextField
              autoFocus
              required
              margin="dense"
              id="name"
              name="name"
              placeholder={activeSearch?.name}
              type="text"
              fullWidth
              variant="outlined"
              value={savedSearchValues.name}
              onChange={(e) => handleChange(e.target.name, e.target.value)}
              inputProps={{
                'aria-label': 'Enter a name for your saved search'
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                }
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
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            tabIndex={0}
            onClick={handleDialogClose}
            color="primary"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                try {
                  handleDialogClose();
                } catch (e) {
                  console.error(e);
                }
              }
            }}
          >
            Cancel
          </Button>
          <Button
            tabIndex={0}
            variant="contained"
            onClick={() => {
              try {
                handleSave(savedSearchValues);
                setUpdateDialogOpen(false);
                savedSearchValues.name = '';
              } catch (e) {
                console.error(e);
              }
            }}
            disabled={
              formErrors.name ||
              formErrors.duplicate ||
              !savedSearchValues.name.trim()
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                try {
                  handleSave(savedSearchValues);
                  setUpdateDialogOpen(false);
                  savedSearchValues.name = '';
                } catch (e) {
                  console.error(e);
                }
              }
            }}
            color="primary"
            autoFocus
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={saveDialogOpen}
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
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                }
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
          <Button
            tabIndex={0}
            onClick={handleCloseModal}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                try {
                  handleCloseModal();
                } catch (e) {
                  console.error(e);
                }
              }
            }}
            aria-label="Cancel and close the dialog"
          >
            Cancel
          </Button>
          <Button
            tabIndex={0}
            variant="contained"
            type="submit"
            disabled={
              formErrors.name ||
              formErrors.duplicate ||
              !savedSearchValues.name.trim()
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                try {
                  if (formErrors.name) {
                    return;
                  }
                  handleSave(savedSearchValues);
                  handleCloseModal();
                } catch (e) {
                  console.error(e);
                }
              }
            }}
            aria-label="Save the search"
            color="primary"
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
