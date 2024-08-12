import * as React from 'react';
import { ContextType } from 'context';
import { withSearch } from '@elastic/react-search-ui';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import { TestDrawerInteriorWithSearch } from './TestDrawer';
import { OrganizationSearch } from './OrganizationSearch';
import { matchPath } from 'utils/matchPath';
import { useLocation } from 'react-router-dom';

export const drawerWidth = 300;

export const FilterDrawer: React.FC<
  ContextType & { isFilterDrawerOpen: boolean }
> = (props) => {
  const {
    addFilter,
    removeFilter,
    filters,
    facets,
    clearFilters,
    searchTerm,
    setSearchTerm,
    isFilterDrawerOpen
  } = props;

  const { pathname } = useLocation();

  // const [open, setOpen] = React.useState(false);
  // const [mobileOpen, setMobileOpen] = React.useState(false);
  // const [isClosing, setIsClosing] = React.useState(false);

  const updateSearchTerm = (term: string) => {
    setSearchTerm(term);
  };

  // const toggleDrawer = (newOpen: boolean) => () => {
  //   setOpen(newOpen);
  // };

  // const handleDrawerClose = () => {
  //   setIsClosing(true);
  //   setMobileOpen(false);
  // };

  // const handleDrawerTransitionEnd = () => {
  //   setIsClosing(false);
  // };

  // const handleDrawerToggle = () => {
  //   if (!isClosing) {
  //     setMobileOpen(!mobileOpen);
  //   }
  // };

  // const { userLevel } = useUserLevel();

  const DrawerList = (
    <Box sx={{ width: 300 }} role="presentation">
      <OrganizationSearch />
      {matchPath(
        ['/inventory', '/inventory/domains', '/inventory/vulnerabilities'],
        pathname
      ) ? (
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
      ) : (
        <></>
      )}
    </Box>
  );

  return (
    <Drawer
      open={isFilterDrawerOpen}
      variant="persistent"
      sx={{
        width: drawerWidth,
        overflow: 'scroll',
        '&::-webkit-scrollbar': {
          display: 'none'
        },
        height: 'calc(100vh - 24px)'
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
