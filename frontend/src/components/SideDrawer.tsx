import * as React from 'react';
import { ContextType } from 'context';
import { withSearch } from '@elastic/react-search-ui';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import MenuIcon from '@mui/icons-material/Menu';
import { IconButton } from '@mui/material';
import { TestDrawerInteriorWithSearch } from './TestDrawer';
import { OrganizationSearch } from './OrganizationSearch';

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

  // const [open, setOpen] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [isClosing, setIsClosing] = React.useState(false);

  const updateSearchTerm = (term: string) => {
    setSearchTerm(term);
  };

  // const toggleDrawer = (newOpen: boolean) => () => {
  //   setOpen(newOpen);
  // };

  const handleDrawerClose = () => {
    setIsClosing(true);
    setMobileOpen(false);
  };

  const handleDrawerTransitionEnd = () => {
    setIsClosing(false);
  };

  const handleDrawerToggle = () => {
    if (!isClosing) {
      setMobileOpen(!mobileOpen);
    }
  };

  const DrawerList = (
    <Box sx={{ width: 300 }} role="presentation">
      <OrganizationSearch />
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
      <IconButton
        onClick={handleDrawerToggle}
        sx={{ mr: 2, display: { sm: 'none' } }}
      >
        <MenuIcon />
      </IconButton>
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onTransitionEnd={handleDrawerTransitionEnd}
        onClose={handleDrawerClose}
        ModalProps={{
          keepMounted: true // Better open performance on mobile.
        }}
        sx={{
          display: { xs: 'block', sm: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box' }
        }}
      >
        {DrawerList}
      </Drawer>
      {/* <Drawer
        variant="permanent"
        style={{ backgroundColor: 'red'}}
        sx={{
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box' }
        }}
        open
      >
        {DrawerList}
      </Drawer> */}
      <Box
        height="calc(100vh - 24px)"
        maxHeight="calc(100vh - 24px)"
        overflow="scroll"
        display="flex"
        bgcolor="white"
      >
        {DrawerList}
      </Box>
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
