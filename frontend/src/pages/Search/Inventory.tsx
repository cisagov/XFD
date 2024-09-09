import React, { useEffect, useMemo, useRef, useState } from 'react';
import { classes, Root } from './Styling/dashboardStyle';
import { Subnav } from 'components';
import { ResultCard } from './ResultCard';
import {
  Button,
  Paper,
  FormControl,
  Select,
  MenuItem,
  Typography,
  Box,
  Stack
} from '@mui/material';
import { Pagination } from '@mui/material';
import { withSearch } from '@elastic/react-search-ui';
import { ContextType } from '../../context/SearchProvider';
import { SortBar } from './SortBar';
import { useAuthContext } from 'context';
import { FilterTags } from './FilterTags';
import { SavedSearch } from 'types';
import { useBeforeunload } from 'react-beforeunload';
import { NoResults } from 'components/NoResults';
import { exportCSV } from 'components/ImportExport';
import { SaveSearchModal } from 'components/SaveSearchModal/SaveSearchModal';

export const DashboardUI: React.FC<ContextType & { location: any }> = (
  props
) => {
  const {
    current,
    setCurrent,
    resultsPerPage,
    setResultsPerPage,
    filters,
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
  const { apiPost, setLoading, showAllOrganizations, currentOrganization } =
    useAuthContext();

  const advanceFiltersReq = filters.length > 1 || searchTerm !== ''; //Prevents a user from saving a search without advanced filters

  const search:
    | (SavedSearch & {
        editing?: boolean;
      })
    | undefined = localStorage.getItem('savedSearch')
    ? JSON.parse(localStorage.getItem('savedSearch')!)
    : undefined;

  useEffect(() => {
    if (props.location.search === '') {
      // Search on initial load
    }
    return () => {
      localStorage.removeItem('savedSearch');
    };
  }, [setSearchTerm, props.location.search]);

  useBeforeunload((event) => {
    localStorage.removeItem('savedSearch');
  });

  const fetchDomainsExport = async (): Promise<string> => {
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
        if ('rootDomains' in currentOrganization)
          body.organizationId = currentOrganization.id;
        else body.tagId = currentOrganization.id;
      }
      const { url } = await apiPost('/search/export', {
        body
      });
      return url!;
    } catch (e) {
      console.error(e);
      return '';
    }
  };

  const filtersToDisplay = useMemo(() => {
    if (searchTerm !== '') {
      return [
        ...filters,
        {
          field: 'query',
          values: [searchTerm],
          onClear: () => setSearchTerm('', { shouldClearFilters: false })
        }
      ];
    }
    return filters;
  }, [filters, searchTerm, setSearchTerm]);

  console.log(filtersToDisplay);

  return (
    <Root className={classes.root}>
      <Subnav
        items={[
          { title: 'Search Results', path: '/inventory', exact: true },
          { title: 'All Domains', path: '/inventory/domains' },
          { title: 'All Vulnerabilities', path: '/inventory/vulnerabilities' }
        ]}
        styles={{
          paddingLeft: '0%'
        }}
      />
      <Box
        position="relative"
        height="calc(100% - 32px - 32px - 46px - 10px)"
        maxHeight="100%"
        width="100%"
        display="flex"
        flexWrap="nowrap"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
      >
        <Box width="90%" height="100%" display="flex" flexDirection="column">
          <FilterTags filters={filtersToDisplay} removeFilter={removeFilter} />
          <Stack
            spacing={2}
            direction="row"
            alignItems="center"
            justifyContent="space-between"
          >
            <SortBar
              sortField={sortField}
              sortDirection={sortDirection}
              setSort={setSort}
              isFixed={resultsScrolled}
              existingSavedSearch={search}
              advancedFiltersReq={advanceFiltersReq}
            />
            <SaveSearchModal
              search={search}
              searchTerm={searchTerm}
              filters={filters}
              totalResults={totalResults}
              sortField={''}
              sortDirection={''}
              advancedFiltersReq={advanceFiltersReq}
            />
          </Stack>
          <Box
            height="100%"
            flexDirection="column"
            flexWrap="nowrap"
            gap="1rem"
            alignItems="stretch"
            display="flex"
            position="relative"
            padding="0 0 2rem 0"
            sx={{ overflowY: 'auto' }}
          >
            {noResults ? (
              <Box
                display="flex"
                flex="1"
                alignItems="center"
                justifyContent="center"
                height="100%"
              >
                <NoResults
                  message={"We don't see any results that match your criteria."}
                ></NoResults>
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
        </Box>
      </Box>
      <Paper className={classes.pagination}>
        <span>
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
        </span>
        <Pagination
          count={totalPages}
          page={current}
          onChange={(_, page) => setCurrent(page)}
          color="primary"
          size="small"
        />
        <FormControl
          variant="outlined"
          className={classes.pageSize}
          size="small"
        >
          <Typography id="results-per-page-label">Results per page:</Typography>
          <Select
            id="teststa"
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
        <Button
          variant="outlined"
          className={classes.exportButton}
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
      </Paper>
    </Root>
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
    clearFilters,
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
    clearFilters,
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
