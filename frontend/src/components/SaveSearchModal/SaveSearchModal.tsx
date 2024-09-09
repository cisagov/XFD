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
import { Vulnerability } from 'types';
import { Save } from '@mui/icons-material';

interface SaveSearchModalProps {
  search: any;
  searchTerm: string;
  // setSearchTerm: any;
  filters: any;
  totalResults: number;
  sortField: string;
  sortDirection: string;
}

export const SaveSearchModal: React.FC<SaveSearchModalProps> = (props) => {
  const {
    search,
    searchTerm,
    // setSearchTerm,
    filters,
    totalResults,
    sortField,
    sortDirection
  } = props;
  const [open, setOpen] = useState(false);
  const [formErrors, setFormErrors] = useState({
    name: false,
    duplicate: false
  });
  const { apiPost, apiPut } = useAuthContext();
  const history = useHistory();

  // Could be used for validation purposes in new dialogue
  const { savedSearches } = useSavedSearchContext();

  const [savedSearchValues, setSavedSearchValues] = useState<
    Partial<SavedSearch> & {
      name: string;
      vulnerabilityTemplate: Partial<Vulnerability>;
    }
  >(
    search
      ? search
      : {
          name: '',
          vulnerabilityTemplate: {},
          createVulnerabilities: false
        }
  );

  const handleChange = (name: string, value: any) => {
    setSavedSearchValues((values) => ({
      ...values,
      [name]: value
    }));

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
        // TODO: verify search is being passed properly
        await apiPut('/saved-searches/' + search.id, body);
      } else {
        await apiPost('/saved-searches/', body);
      }
      history.push('/inventory');
      window.location.reload();
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

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log(props);

    if (formErrors.name) {
      return;
    }
    handleSave(savedSearchValues);
    handleCloseModal();
  };

  // Validate Saved Search Name
  const validation = (name: string): boolean => {
    const nameRegex = /^(?=.*[A-Za-z0-9])[A-Za-z0-9\s\'\-]+$/;
    return nameRegex.test(name);
  };

  return (
    <>
      <Button variant="contained" onClick={handleOpenModal} endIcon={<Save />}>
        Save Search
      </Button>
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
          {/* <Button onClick={() => {
            savedSearches.map((search) => {
            console.log(search.name);
            });
          }}> Press</Button> */}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal}>Cancel</Button>
          <Button
            type="submit"
            disabled={formErrors.name || formErrors.duplicate}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
