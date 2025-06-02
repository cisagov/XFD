import React, { FC } from 'react';
import { ContextType } from 'context';
import { withSearch } from '@elastic/react-search-ui';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import { DrawerInterior } from './DrawerInterior';
import { RegionAndOrganizationFilters } from './RegionAndOrganizationFilters';
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import { matchPath } from 'utils/matchPath';
import { useLocation } from 'react-router-dom';
import { Stack } from '@mui/system';
import { Toolbar, Typography } from '@mui/material';

export const drawerWidth = 300;

export const FilterDrawer: FC<
  ContextType & {
    isFilterDrawerOpen: boolean;
    // isMobile: boolean;
    setIsFilterDrawerOpen: (isOpen: boolean) => void;
    initialFilters: any[];
  }
> = (props) => {
  const {
    // isMobile,
    isFilterDrawerOpen,
    setIsFilterDrawerOpen,
    addFilter,
    removeFilter,
    facets,
    search_term,
    setSearchTerm,
    filters,
    initialFilters
  } = props;
  const { pathname } = useLocation();

  const DrawerList = (
    <Box sx={{ width: drawerWidth }} role="presentation">
      <Toolbar sx={{ justifyContent: 'center' }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography variant="h6" component="h3">
            Filters
          </Typography>
          <FilterAltIcon />
        </Stack>
      </Toolbar>
      <RegionAndOrganizationFilters
        addFilter={addFilter}
        removeFilter={removeFilter}
        filters={filters}
        setSearchTerm={setSearchTerm}
        search_term={search_term}
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
          search_term={search_term}
          setSearchTerm={setSearchTerm}
          initialFilters={initialFilters}
        />
      ) : (
        <></>
      )}
    </Box>
  );

  return (
    <Drawer
      open={isFilterDrawerOpen}
      // variant={isMobile ? 'temporary' : 'persistent'}
      variant="temporary"
      // ModalProps={{ keepMounted: isMobile }}
      ModalProps={{ keepMounted: true }}
      onClose={() => setIsFilterDrawerOpen(false)}
      sx={{
        width: drawerWidth,
        overflow: 'scroll',
        '&::-webkit-scrollbar': {
          display: 'none'
        },
        // height: isMobile ? 'unset' : 'calc(100vh - 24px)'
        height: 'unset'
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
    search_term,
    setSearchTerm
  }: ContextType) => ({
    addFilter,
    removeFilter,
    filters,
    facets,
    search_term,
    setSearchTerm
  })
)(FilterDrawer);
