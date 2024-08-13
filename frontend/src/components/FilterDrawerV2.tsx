import * as React from 'react';
import { ContextType } from 'context';
import { withSearch } from '@elastic/react-search-ui';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import { DrawerInterior } from './DrawerInterior';
import { OrganizationSearch } from './OrganizationSearch';
import { matchPath } from 'utils/matchPath';
import { useLocation } from 'react-router-dom';

export const drawerWidth = 300;

export const FilterDrawer: React.FC<
  ContextType & {
    isFilterDrawerOpen: boolean;
    isMobile: boolean;
    setIsFilterDrawerOpen: (isOpen: boolean) => void;
  }
> = (props) => {
  const {
    isMobile,
    isFilterDrawerOpen,
    setIsFilterDrawerOpen,
    addFilter,
    removeFilter,
    facets,
    clearFilters,
    searchTerm,
    setSearchTerm,
    filters
  } = props;
  const { pathname } = useLocation();

  const DrawerList = (
    <Box sx={{ width: drawerWidth }} role="presentation">
      <OrganizationSearch
        addFilter={addFilter}
        removeFilter={removeFilter}
        filters={filters}
      />
      {matchPath(
        ['/inventory', '/inventory/domains', '/inventory/vulnerabilities'],
        pathname
      ) ? (
        <DrawerInterior
          addFilter={addFilter}
          removeFilter={removeFilter}
          filters={filters}
          facets={facets}
          clearFilters={filters.length > 0 ? () => clearFilters([]) : undefined}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
        />
      ) : (
        <></>
      )}
    </Box>
  );

  return (
    <Drawer
      open={isFilterDrawerOpen}
      variant={isMobile ? 'temporary' : 'persistent'}
      keepMounted={isMobile}
      onClose={() => setIsFilterDrawerOpen(false)}
      sx={{
        width: drawerWidth,
        overflow: 'scroll',
        '&::-webkit-scrollbar': {
          display: 'none'
        },
        height: isMobile ? 'unset' : 'calc(100vh - 24px)'
      }}
      PaperProps={{ style: { position: 'unset' } }}
    >
      {DrawerList}
    </Drawer>
  );
};

export const FilterDrawerV2 = withSearch(
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
)(FilterDrawer);
