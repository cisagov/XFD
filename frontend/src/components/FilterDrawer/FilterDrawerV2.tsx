import React, { FC } from 'react';
import { useLocation } from 'react-router-dom';
import { withSearch } from '@elastic/react-search-ui';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/system/Stack';
import Typography from '@mui/material/Typography';
import CloseIcon from '@mui/icons-material/Close';
import { ContextType, useSavedSearchContext } from 'context';
import { DrawerInterior } from './DrawerInterior';
import { RegionAndOrganizationFilters } from './RegionAndOrganizationFilters';
import { matchPath } from 'utils/stringUtils';
import { useAreFiltersDefault } from '@/hooks/useAreFiltersDefault';
import { VSDashRegionAndOrgFilters } from './VSDashRegionAndOrgFilters';
import { ROUTES } from '@/constants/routes';

export const drawerWidth = 278;

export const FilterDrawer: FC<
  ContextType & {
    isFilterDrawerOpen: boolean;
    isMobile: boolean;
    setIsFilterDrawerOpen: (isOpen: boolean) => void;
    initialFilters: any[];
    topOffset: number;
  }
> = (props) => {
  const {
    isMobile,
    isFilterDrawerOpen,
    setIsFilterDrawerOpen,
    addFilter,
    removeFilter,
    facets,
    searchTerm,
    setSearchTerm,
    filters,
    initialFilters,
    autocompletedResults,
    autocompletedSuggestions,
    results,
    topOffset
  } = props;
  const { pathname } = useLocation();
  const { setActiveSearchId } = useSavedSearchContext();

  const restoreInitialFilters = () => {
    if (matchPath([ROUTES.INVENTORY], pathname)) {
      initialFilters.forEach((filter) => {
        filter.values.forEach((value: string) => {
          addFilter(filter.field, value, 'any');
        });
      });
    }
  };

  const defaultFilters = useAreFiltersDefault(filters, initialFilters);

  const clearFiltersAndSearch = () => {
    setSearchTerm('', {
      shouldClearFilters: true,
      autocompleteResults: false
    });
    restoreInitialFilters();
    setActiveSearchId('');
  };

  const [expanded, setExpanded] = React.useState<string | false>('panel1');

  const handleExpanded =
    (panel: string) => (event: React.SyntheticEvent, newExpanded: boolean) => {
      setExpanded(newExpanded ? panel : false);
    };
  const theme = useTheme();
  const DrawerList = (
    <Stack justifyContent={'space-between'} height="100vh">
      <Box role="presentation">
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          height={84}
          px={2}
          sx={{ borderBottom: `.5px solid ${theme.palette.neutrals.light}` }}
        >
          <Typography variant="h3" component="h3">
            Filter
          </Typography>

          <IconButton
            onClick={() => setIsFilterDrawerOpen(false)}
            sx={{
              color: 'neutrals.black',
              '&:hover': {
                backgroundColor: 'neutrals.lightGray'
              }
            }}
            aria-label="close-filter-drawer"
          >
            <CloseIcon />
          </IconButton>
        </Stack>

        {matchPath([ROUTES.INVENTORY], pathname) && (
          <RegionAndOrganizationFilters
            addFilter={addFilter}
            removeFilter={removeFilter}
            filters={filters}
            facets={facets}
            setSearchTerm={setSearchTerm}
            searchTerm={searchTerm}
            autocompletedResults={autocompletedResults}
            autocompletedSuggestions={autocompletedSuggestions}
            results={results}
            initialFilters={initialFilters}
            expanded={expanded}
            handleExpanded={handleExpanded}
          />
        )}
        {matchPath([ROUTES.HOME, ROUTES.VSDASHBOARD], pathname) && (
          <VSDashRegionAndOrgFilters
            addFilter={addFilter}
            removeFilter={removeFilter}
            filters={filters}
          />
        )}
        {matchPath(
          [ROUTES.INVENTORY, ROUTES.DOMAINS, ROUTES.VULNERABILITIES],
          pathname
        ) && (
          <DrawerInterior
            addFilter={addFilter}
            removeFilter={removeFilter}
            filters={filters}
            facets={facets}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            initialFilters={initialFilters}
            expanded={expanded}
            handleExpanded={handleExpanded}
          />
        )}
      </Box>
      {matchPath([ROUTES.INVENTORY], pathname) && (
        <Box>
          <Box
            paddingBottom={5}
            display="flex"
            width="100%"
            justifyContent="center"
          >
            <Button
              onClick={clearFiltersAndSearch}
              disabled={defaultFilters}
              sx={{
                color: 'primary.dark',
                fontSize: '14px',
                fontWeight: 'bold',
                lineHeight: '20px',
                letterSpacing: '0.1em'
              }}
              aria-label="Reset Filters"
            >
              Reset
            </Button>
          </Box>
        </Box>
      )}
    </Stack>
  );

  return (
    <Drawer
      container={document.getElementById('main-layout')}
      open={isFilterDrawerOpen}
      variant={isMobile ? 'temporary' : 'persistent'}
      ModalProps={{ keepMounted: isMobile }}
      onClose={() => setIsFilterDrawerOpen(false)}
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          position: 'fixed',
          width: drawerWidth,
          overflow: 'auto',
          backgroundColor: 'neutrals.white',
          top: isMobile ? 0 : topOffset - 84,
          height: isMobile ? '100%' : `calc(100% - (${topOffset}px - 84px))`,
          minHeight: `calc(100% - ${topOffset}px)`,
          zIndex: (theme) => theme.zIndex.appBar
        }
      }}
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
    searchTerm,
    setSearchTerm,
    autocompletedResults,
    autocompletedSuggestions,
    results
  }: ContextType) => ({
    addFilter,
    removeFilter,
    filters,
    facets,
    searchTerm,
    setSearchTerm,
    autocompletedResults,
    autocompletedSuggestions,
    results
  })
)(FilterDrawer);
