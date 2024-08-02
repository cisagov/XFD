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
    <Box sx={{ width: 250 }} role="presentation">
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
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box' }
        }}
        open
      >
        {DrawerList}
      </Drawer>
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
