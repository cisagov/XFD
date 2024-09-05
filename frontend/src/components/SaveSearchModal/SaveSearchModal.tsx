import React, { useState, useEffect } from 'react';
import { useHistory } from 'react-router-dom';
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
import { useBeforeunload } from 'react-beforeunload';

import { useSavedSearchContext } from '../../context/SavedSearchContext';

interface SaveSearchModalProps {
  props: any;
}

export default function SaveSearchModal(props: any) {
  const {
    searchTerm,
    setSearchTerm,
    filters,
    totalResults,
    sortField,
    sortDirection
  } = props;
  const [open, setOpen] = useState(false);

  const { apiPost, apiPut } = useAuthContext();

  const search:
    | (SavedSearch & {
        editing?: boolean;
      })
    | undefined = localStorage.getItem('savedSearch')
    ? JSON.parse(localStorage.getItem('savedSearch')!)
    : undefined;
  const history = useHistory();
  const [savedSearchValues, setSavedSearchValues] = useState<
    Partial<SavedSearch> & {
      name: string;
      // vulnerabilityTemplate: Partial<Vulnerability>;
    }
  >(
    search
      ? search
      : {
          name: ''
          // vulnerabilityTemplate: {},
          // createVulnerabilities: false
        }
  );

  // const onTextChange: React.ChangeEventHandler<
  //   HTMLInputElement | HTMLSelectElement
  // > = (e) => handleChange(e.target.name, e.target.value);

  const handleChange = (name: string, value: any) => {
    setSavedSearchValues((values) => ({
      ...values,
      [name]: value
    }));
  };

  // TODO: Need to verify if needed
  // useEffect(() => {
  //   if (props.location.search === '') {
  //     // Search on initial load
  //     setSearchTerm('', { shouldClearFilters: false });
  //   }
  //   return () => {
  //     localStorage.removeItem('savedSearch');
  //     setSearchTerm('', { shouldClearFilters: false });
  //   };
  // }, [setSearchTerm, props.location.search]);

  // useBeforeunload((event) => {
  //   localStorage.removeItem('savedSearch');
  // });

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
      console.log('Search: ', props.location.search);

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

  // TODO
  const handleCloseModal = () => {
    setOpen(false);
  };
  const handleOpenModal = () => {
    setOpen(true);
  };
  // TODO
  // const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  //   const { name, value } = e.target;
  //   setSavedSearchValues((prevValues) => ({
  //     ...prevValues,
  //     [name]: value
  //   }));
  // };
  // TODO

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log(props);
    handleSave(savedSearchValues);
    handleCloseModal();
  };

  return (
    <>
      <Button onClick={handleOpenModal}>Open Modal</Button>
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
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal}>Cancel</Button>
          <Button type="submit">Save</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
