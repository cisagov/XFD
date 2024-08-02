import * as React from 'react';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import Divider from '@mui/material/Divider';
import MenuIcon from '@mui/icons-material/Menu';
import { IconButton, Toolbar, Typography } from '@mui/material';
import { ContextType } from 'context';
import { withSearch } from '@elastic/react-search-ui';
import { TestDrawerInteriorWithSearch } from './TestDrawer';
export const SideDrawer: React.FC<ContextType & { location: any }> = (
  props
) => {
  const {
    addFilter,
    removeFilter,
    filters,
    facets,
    clearFilters,
    searchTerm,
    setSearchTerm
  } = props;

  const [open, setOpen] = React.useState(false);

  const updateSearchTerm = (term: string) => {
    setSearchTerm(term);
  };

  const toggleDrawer = (newOpen: boolean) => () => {
    setOpen(newOpen);
  };

  const DrawerList = (
    <Box sx={{ width: 350 }} role="presentation">
      <Toolbar>
        <Typography>Filter Drawer</Typography>
      </Toolbar>
      <Divider />
      <TestDrawerInteriorWithSearch
        addFilter={addFilter}
        removeFilter={removeFilter}
        filters={filters}
        facets={facets}
        clearFilters={filters.length > 0 ? () => clearFilters([]) : undefined}
        updateSearchTerm={updateSearchTerm}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
      />
    </Box>
  );

  return (
    <div>
      {/* <Button>Open drawer</Button> */}
      <Drawer open={open} onClose={toggleDrawer(false)}>
        {DrawerList}
      </Drawer>
      <IconButton onClick={toggleDrawer(true)}>
        <MenuIcon />
      </IconButton>
    </div>
  );
};

export const SideDrawerWithSearch = withSearch(
  ({
    addFilter,
    removeFilter,
    filters,
    facets,
    clearFilters,
    searchTerm,
    setSearchTerm
  }: ContextType) => ({
    addFilter,
    removeFilter,
    filters,
    facets,
    clearFilters,
    searchTerm,
    setSearchTerm
  })
)(SideDrawer);
