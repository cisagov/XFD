import React from 'react';
import {
  IconButton,
  FormControl,
  MenuItem,
  Select,
  SelectProps,
  Stack,
  Typography
} from '@mui/material';
import { ArrowUpward, ArrowDownward } from '@mui/icons-material';
import { ContextType } from 'context/SearchProvider';

interface Props {
  sortField: ContextType['sortField'];
  sortDirection?: ContextType['sortDirection'];
  setSort: ContextType['setSort'];
  isFixed: boolean;
  children?: React.ReactNode;
  advancedFiltersReq?: boolean;
}

export const SortBar: React.FC<Props> = (props) => {
  const { sortField, sortDirection, setSort, children } = props;

  const toggleDirection = () => {
    setSort(sortField, sortDirection === 'asc' ? 'desc' : 'asc');
  };

  const onSetSortField: SelectProps['onChange'] = (e) => {
    setSort(e.target.value as string, 'asc');
  };

  return (
    <Stack
      direction="row"
      spacing={2}
      alignItems="center"
      flexWrap="wrap"
      sx={{ mb: 2 }}
    >
      <IconButton
        onClick={toggleDirection}
        aria-label={`Sort ${
          sortDirection === 'asc' ? 'Descending' : 'Ascending'
        }`}
      >
        {sortDirection === 'asc' ? <ArrowUpward /> : <ArrowDownward />}
      </IconButton>
      <Typography id="sort-by-label" variant="body1">
        Sort by:
      </Typography>
      <FormControl size="small">
        <Select
          labelId="sort-by-label"
          value={sortField ?? 'name'}
          onChange={onSetSortField}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="name">Domain Name</MenuItem>
          <MenuItem value="ip">IP</MenuItem>
          <MenuItem value="updated_at">Last Seen</MenuItem>
          <MenuItem value="created_at">First Seen</MenuItem>
        </Select>
      </FormControl>
      {children}
    </Stack>
  );
};
