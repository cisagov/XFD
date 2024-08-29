import React, { useState } from 'react';
import SaveSearchModal from '../../components/SaveSearchModal/SaveSearchModal';
import { classes, Root } from './Styling/sortBarStyle';
import {
  Button,
  Select,
  FormControl,
  MenuItem,
  SelectProps,
  IconButton
} from '@mui/material';
import { ArrowUpward, ArrowDownward, Save } from '@mui/icons-material';
import { ContextType } from 'context/SearchProvider';
import { SavedSearch } from 'types';

interface Props {
  sortField: ContextType['sortField'];
  sortDirection?: ContextType['sortDirection'];
  setSort: ContextType['setSort'];
  saveSearch?(): void;
  isFixed: boolean;
  existingSavedSearch?: SavedSearch;
  children?: React.ReactNode;
  advancedFiltersReq?: boolean;
}

export const SortBar: React.FC<Props> = (props) => {
  const {
    sortField,
    sortDirection,
    setSort,
    saveSearch,
    children,
    existingSavedSearch,
    advancedFiltersReq
  } = props;

  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const toggleDirection = () => {
    setSort(sortField, sortDirection === 'asc' ? 'desc' : 'asc');
  };

  const onSetSortField: SelectProps['onChange'] = (e) => {
    setSort(e.target.value as string, 'asc');
  };

  return (
    <Root className={classes.root}>
      <div className={classes.sortMenu}>
        <IconButton
          className={classes.toggleDirection}
          onClick={toggleDirection}
          aria-label={`Sort ${
            sortDirection === 'asc' ? 'Descending' : 'Ascending'
          }`}
        >
          {!sortDirection || sortDirection === 'desc' ? (
            <ArrowDownward />
          ) : (
            <ArrowUpward />
          )}
        </IconButton>
        <Button variant="outlined" onClick={handleClickOpen}>
          Open Save Search Modal
        </Button>
        <SaveSearchModal open={open} handleClose={handleClose} />

        <span id="sort-by-label">Sort by: </span>
        <FormControl className={classes.openFields}>
          <Select
            disableUnderline
            labelId="sort-by-label"
            value={sortField}
            onChange={onSetSortField}
            classes={{ select: classes.selectInp }}
            sx={{
              paddingLeft: 1
            }}
          >
            <MenuItem classes={{ root: classes.option }} value="name">
              Domain Name
            </MenuItem>
            <MenuItem classes={{ root: classes.option }} value="ip">
              IP
            </MenuItem>
            <MenuItem classes={{ root: classes.option }} value="updatedAt">
              Last Seen
            </MenuItem>
            <MenuItem classes={{ root: classes.option }} value="createdAt">
              First Seen
            </MenuItem>
          </Select>
        </FormControl>
      </div>
      {children}
      <div>
        {saveSearch && (
          <Button
            variant="contained"
            onClick={saveSearch}
            disabled={!advancedFiltersReq}
          >
            {existingSavedSearch ? 'Update Saved Search' : 'Save Search'}
          </Button>
        )}
      </div>
    </Root>
  );
};
