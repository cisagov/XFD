import React, { useEffect, useState } from 'react';
import { ResultCard } from './ResultCard';
import {
  Button,
  Paper,
  FormControl,
  Select,
  MenuItem,
  Typography,
  Box,
  Stack,
  useTheme
} from '@mui/material';
import { Pagination } from '@mui/material';
import { withSearch } from '@elastic/react-search-ui';
import { ContextType } from 'context/SearchProvider';
import { SortBar } from './SortBar';
import { useAuthContext } from 'context';
import { NoResults } from 'components/NoResults';
import { exportCSV } from 'components/ImportExport';
import { useStaticsContext } from 'context/StaticsContext';
import { useUserLevel } from 'hooks/useUserLevel';
import { useUserTypeFilters } from 'hooks/useUserTypeFilters';
import { FiberManualRecordRounded } from '@mui/icons-material';
import { FindingsHeader } from 'components/FindingsLibrary/FindingsHeader';

export const DashboardUI: React.FC<ContextType & { location: any }> = (
  props
) => {
  const {
    current,
    setCurrent,
    resultsPerPage,
    setResultsPerPage,
    filters,
    addFilter,
    removeFilter,
    results,
    sortDirection,
    sortField,
    setSort,
    totalPages,
    totalResults,
    setSearchTerm,
    searchTerm,
    noResults
  } = props;

  const [selectedDomain, setSelectedDomain] = useState('');
  const [resultsScrolled] = useState(false);
  const {
    apiPost,
    setLoading,
    showAllOrganizations,
    currentOrganization,
    user
  } = useAuthContext();

  const advanceFiltersReq = filters.length > 1 || searchTerm !== ''; //Prevents a user from saving a search without advanced filters

  const allowExport =
    filters?.find((filter) => filter.field === 'organization_id')?.values
      ?.length == 1;

  const fetchDomainsExport = async (): Promise<string | null> => {
    try {
      const body: any = {
        current,
        filters,
        resultsPerPage,
        searchTerm,
        sortDirection,
        sortField
      };
      if (!showAllOrganizations && currentOrganization) {
        if ('root_domains' in currentOrganization)
          body.organization_id = [currentOrganization.id];
        else body.tagId = [currentOrganization.id];
      }
      const { url } = await apiPost('/search/export', {
        body
      });
      return url!;
    } catch (e) {
      console.error(e);
      return null;
    }
  };
  const userLevel = useUserLevel().userLevel;

  const { regions } = useStaticsContext();
  const initialFiltersForUser = useUserTypeFilters(regions, user, userLevel);

  const resetFilters = () => {
    filters.forEach((filter) => {
      removeFilter(filter.field, filter.values[0], filter.type);
    });
    initialFiltersForUser.forEach(
      (filter) => {
        filter.values.forEach((value) => {
          addFilter(filter.field, value, filter.type);
        });
      },
      setSearchTerm('', { shouldClearFilters: false })
    );
  };

  useEffect(() => {
    filters.forEach((filter) => {
      removeFilter(filter.field, filter.values[0], filter.type);
    });
    initialFiltersForUser.forEach((filter) => {
      filter.values.forEach((value) => {
        addFilter(filter.field, value, filter.type);
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const FiltersApplied: React.FC = () => {
    const theme = useTheme();
    return (
      <Stack direction="row" alignItems="center" spacing={1}>
        <FiberManualRecordRounded
          sx={{
            color: theme.palette.primary.main,
            height: '1rem',
            width: '1rem'
          }}
        />
        <Typography color="textSecondary">Filters Applied</Typography>
      </Stack>
    );
  };

  const nonInitialFilters = filters.filter((currentFilter) => {
    const initial = initialFiltersForUser.find(
      (initFilter) => initFilter.field === currentFilter.field
    );
    if (!initial) return true;

    const currentVals = Array.isArray(currentFilter.values)
      ? currentFilter.values
      : [currentFilter.values];
    const initialVals = Array.isArray(initial.values)
      ? initial.values
      : [initial.values];

    if (currentFilter.field === 'organization_id') {
      const currentIds = currentVals.map((org: any) => org.id);
      const initialIds = initialVals.map((org: any) => org.id);
      if (currentIds.length !== initialIds.length) return true;
      return !currentIds.every((id: any) => initialIds.includes(id));
    } else {
      if (currentVals.length !== initialVals.length) return true;
      return !currentVals.every((val: any) => initialVals.includes(val));
    }
  });

  return (
    <Box
      display="flex"
      flexDirection="column"
      minHeight="100vh"
      maxWidth="1152px"
      width="100%"
      margin="auto"
    >
      <FindingsHeader />
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        pb={2}
      >
        {nonInitialFilters.length > 0 && <FiltersApplied />}
        {/* Keeps SortBar fixed to the right side of the screen */}
        <Box sx={{ flexGrow: 1 }} />
        <SortBar
          sortField={sortField}
          sortDirection={sortDirection}
          setSort={setSort}
          isFixed={resultsScrolled}
          advancedFiltersReq={advanceFiltersReq}
        />
      </Stack>
      <Box flexGrow={1} display="flex" flexDirection="column">
        {noResults ? (
          <Box
            display="flex"
            flex="1"
            alignItems="center"
            justifyContent="center"
            height="100%"
          >
            <Stack spacing={3} alignItems="center" direction={'column'}>
              <NoResults
                message={"We don't see any results that match your criteria."}
              ></NoResults>
              <Button variant="primaryContained" onClick={resetFilters}>
                Reset Filters
              </Button>
            </Stack>
          </Box>
        ) : (
          results.map((result) => (
            <ResultCard
              key={result.id.raw}
              {...result}
              onDomainSelected={(id) => setSelectedDomain(id)}
              selected={result.id.raw === selectedDomain}
            />
          ))
        )}
      </Box>
      <Box
        sx={{
          position: 'sticky',
          bottom: 0,
          width: '100%',
          zIndex: 100,
          backgroundColor: 'background.paper',
          borderTop: 1,
          borderColor: 'divider'
        }}
      >
        <Paper elevation={3} sx={{ px: 2, py: 1.5 }}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            alignItems="center"
            justifyContent="space-between"
            flexWrap="wrap"
          >
            <Typography variant="body2">
              <strong>
                {(totalResults === 0
                  ? 0
                  : (current - 1) * resultsPerPage + 1
                ).toLocaleString()}{' '}
                -{' '}
                {Math.min(
                  (current - 1) * resultsPerPage + resultsPerPage,
                  totalResults
                ).toLocaleString()}
              </strong>{' '}
              of <strong>{totalResults.toLocaleString()}</strong>
            </Typography>
            <Pagination
              count={totalPages}
              page={current}
              onChange={(_, page) => setCurrent(page)}
              color="primary"
              size="small"
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography id="results-per-page-label" variant="body2">
                Results per page:
              </Typography>
              <FormControl size="small" variant="outlined">
                <Select
                  id="results-per-page-select"
                  labelId="results-per-page-label"
                  value={resultsPerPage}
                  onChange={(e) => setResultsPerPage(e.target.value as number)}
                >
                  {[15, 45, 90].map((perPage) => (
                    <MenuItem key={perPage} value={perPage}>
                      {perPage}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
            <Button
              hidden={!allowExport}
              variant="outlined"
              onClick={() =>
                exportCSV(
                  {
                    name: 'domains',
                    getDataToExport: fetchDomainsExport
                  },
                  setLoading
                )
              }
            >
              Export Results
            </Button>
          </Stack>
        </Paper>
      </Box>
    </Box>
  );
};

export const Dashboard = withSearch(
  ({
    addFilter,
    removeFilter,
    results,
    totalResults,
    filters,
    facets,
    searchTerm,
    setSearchTerm,
    autocompletedResults,
    saveSearch,
    sortDirection,
    sortField,
    setSort,
    resultsPerPage,
    setResultsPerPage,
    current,
    setCurrent,
    totalPages,
    noResults
  }: ContextType) => ({
    addFilter,
    removeFilter,
    results,
    totalResults,
    filters,
    facets,
    searchTerm,
    setSearchTerm,
    autocompletedResults,
    saveSearch,
    sortDirection,
    sortField,
    setSort,
    resultsPerPage,
    setResultsPerPage,
    current,
    setCurrent,
    totalPages,
    noResults
  })
)(DashboardUI);
