import React, { useMemo, useState } from 'react';
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
import { NoResults } from 'components/NoResults';
import { exportCSV } from 'components/ImportExport';
import { SaveSearchModal } from 'components/SaveSearchModal/SaveSearchModal';
import { useStaticsContext } from 'context/StaticsContext';
import { useUserLevel } from 'hooks/useUserLevel';
import { useUserTypeFilters } from 'hooks/useUserTypeFilters';

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
    sort_direction,
    sort_field,
    setSort,
    totalPages,
    totalResults,
    setSearchTerm,
    search_term,
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

  const advanceFiltersReq = filters.length > 1 || search_term !== ''; //Prevents a user from saving a search without advanced filters

  const fetchDomainsExport = async (): Promise<string> => {
    try {
      const body: any = {
        current,
        filters,
        resultsPerPage,
        search_term,
        sort_direction,
        sort_field
      };
      if (!showAllOrganizations && currentOrganization) {
        if ('root_domains' in currentOrganization)
          body.organization_id = currentOrganization.id;
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
    if (search_term !== '') {
      return [
        ...filters,
        {
          field: 'query',
          values: [search_term],
          onClear: () => setSearchTerm('', { shouldClearFilters: false })
        }
      ];
    }
    return filters;
  }, [filters, search_term, setSearchTerm]);

  const userLevel = useUserLevel().userLevel;

  const { regions } = useStaticsContext();
  const initialFiltersForUser = useUserTypeFilters(regions, user, userLevel);

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
        width="90%"
        display="flex"
        alignSelf={'anchor-center'}
        flexDirection={'column'}
      >
        <FilterTags filters={filtersToDisplay} removeFilter={removeFilter} />
        <Stack
          spacing={2}
          direction="row"
          alignItems="center"
          justifyContent="space-between"
        >
          <SortBar
            sort_field={sort_field}
            sort_direction={sort_direction}
            setSort={setSort}
            isFixed={resultsScrolled}
            advancedFiltersReq={advanceFiltersReq}
          />
          <SaveSearchModal
            search_term={search_term}
            filters={filters}
            totalResults={totalResults}
            sort_field={''}
            sort_direction={''}
            advancedFiltersReq={advanceFiltersReq}
          />
        </Stack>
      </Box>
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
        overflow="auto"
      >
        <Box
          height="100%"
          width="90%"
          flexDirection="column"
          flexWrap="nowrap"
          gap="1rem"
          alignItems="stretch"
          display="flex"
          position="relative"
          padding="0 0 2rem 0"
        >
          {noResults ? (
            <Box
              display="flex"
              flex="1"
              alignItems="center"
              justifyContent="center"
              height="100%"
            >
              <Stack spacing={2} alignItems="center" direction={'column'}>
                <NoResults
                  message={"We don't see any results that match your criteria."}
                ></NoResults>
                <Button
                  variant="contained"
                  onClick={() =>
                    initialFiltersForUser.forEach((filter) => {
                      filter.values.forEach((value) => {
                        addFilter(filter.field, value, filter.type);
                      });
                    })
                  }
                >
                  {' '}
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
    search_term,
    setSearchTerm,
    autocompletedResults,
    saveSearch,
    sort_direction,
    sort_field,
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
    search_term,
    setSearchTerm,
    autocompletedResults,
    saveSearch,
    sort_direction,
    sort_field,
    setSort,
    resultsPerPage,
    setResultsPerPage,
    current,
    setCurrent,
    totalPages,
    noResults
  })
)(DashboardUI);
