import React from 'react';
import { classes, Root } from './Styling/sortBarStyle';
import {
  Select,
  FormControl,
  MenuItem,
  SelectProps,
  IconButton
} from '@mui/material';
import { ArrowUpward, ArrowDownward } from '@mui/icons-material';
import { ContextType } from 'context/SearchProvider';

interface Props {
  sort_field: ContextType['sort_field'];
  sort_direction?: ContextType['sort_direction'];
  setSort: ContextType['setSort'];
  isFixed: boolean;
  children?: React.ReactNode;
  advancedFiltersReq?: boolean;
}

export const SortBar: React.FC<Props> = (props) => {
  const { sort_field, sort_direction, setSort, children } = props;

  const toggleDirection = () => {
    setSort(sort_field, sort_direction === 'asc' ? 'desc' : 'asc');
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
            sort_direction === 'asc' ? 'Descending' : 'Ascending'
          }`}
        >
          {!sort_direction || sort_direction === 'desc' ? (
            <ArrowDownward />
          ) : (
            <ArrowUpward />
          )}
        </IconButton>
        <span id="sort-by-label">Sort by: </span>
        <FormControl className={classes.openFields}>
          <Select
            labelId="sort-by-label"
            value={sort_field ?? 'name'}
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
            <MenuItem classes={{ root: classes.option }} value="updated_at">
              Last Seen
            </MenuItem>
            <MenuItem classes={{ root: classes.option }} value="created_at">
              First Seen
            </MenuItem>
          </Select>
        </FormControl>
      </div>
      {children}
    </Root>
  );
};
