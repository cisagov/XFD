import React, { useMemo } from 'react';
import {
  AccordionDetails,
  Accordion as MuiAccordion,
  AccordionSummary as MuiAccordionSummary,
  IconButton,
  Stack,
  Typography,
  Box,
  List,
  FormControlLabel,
  ListItem,
  FormGroup,
  Radio,
  useTheme,
  Checkbox
} from '@mui/material';
import {
  DeleteOutline,
  ExpandMore,
  FiberManualRecordRounded
} from '@mui/icons-material';
import { FacetFilter, TaggedArrayInput } from 'components';
import { ContextType } from 'context/SearchProvider';
import { useAuthContext } from 'context';
import { useSavedSearchContext } from 'context/SavedSearchContext';
import { withSearch } from '@elastic/react-search-ui';
import { SaveSearchModal } from '../SaveSearchModal/SaveSearchModal';
import { Facet } from '@elastic/react-search-ui';

interface Props {
  addFilter: ContextType['addFilter'];
  removeFilter: ContextType['removeFilter'];
  filters: ContextType['filters'];
  facets: ContextType['facets'];
  searchTerm: ContextType['searchTerm'];
  setSearchTerm: ContextType['setSearchTerm'];
  totalResults?: ContextType['totalResults'];
  initialFilters: any[];
  expanded?: string | false;
  handleExpanded?: (
    panel: string
  ) => (event: React.SyntheticEvent, newExpanded: boolean) => void;
}

interface SeverityData {
  value: string;
  count: number;
}

interface GroupedData {
  [key: string]: number;
}

const FiltersApplied: React.FC = () => {
  const theme = useTheme();
  return (
    <FiberManualRecordRounded
      sx={{ color: theme.palette.primary.main, height: '1rem', width: '1rem' }}
    />
  );
};

const Accordion = MuiAccordion;
const AccordionSummary = MuiAccordionSummary;

export const DrawerInterior: React.FC<Props> = (props) => {
  const {
    filters,
    addFilter,
    removeFilter,
    facets,
    searchTerm,
    setSearchTerm,
    totalResults = 0, // Default to 0 if not provided
    initialFilters,
    expanded,
    handleExpanded
  } = props;
  const { apiGet, apiDelete } = useAuthContext();

  const {
    savedSearches,
    setSavedSearches,
    setSavedSearchCount,
    activeSearchId,
    setActiveSearchId
  } = useSavedSearchContext();

  const advanceFiltersReq = filters.length > 1 || searchTerm !== '';
  const theme = useTheme();

  const deleteSearch = async (id: string) => {
    try {
      await apiDelete(`/saved-searches/${id}`, { body: {} });
      const updatedSearches = await apiGet('/saved-searches'); // Get current saved searches
      setSavedSearches(updatedSearches.result); // Update the saved searches
      setSavedSearchCount(updatedSearches.result.length); // Update the count
      localStorage.removeItem('savedSearch');
    } catch (e) {
      console.log(e);
    }
  };
  const displaySavedSearch = (id: string) => {
    const savedSearch = savedSearches.find((search) => search.id === id);
    if (savedSearch) {
      setSearchTerm(savedSearch.search_term, {
        shouldClearFilters: true,
        autocompleteResults: false
      });
    }

    savedSearch?.filters?.forEach((filter) => {
      filter.values.forEach((value: string) => {
        addFilter(filter.field, value, 'any');
      });
    });
    setActiveSearchId(id);
  };
  const restoreInitialFilters = () => {
    initialFilters.forEach((filter) => {
      filter.values.forEach((value: string) => {
        addFilter(filter.field, value, 'any');
      });
    });
  };

  const revertSearch = () => {
    setSearchTerm('', {
      shouldClearFilters: true,
      autocompleteResults: false
    });
    restoreInitialFilters();
    setActiveSearchId('');
  };
  const toggleSavedSearches = (id: string) => {
    const savedSearch = savedSearches.filter((search) => search.id === id);

    if (savedSearch) {
      if (!isSavedSearchActive(id)) {
        displaySavedSearch(id);
      } else {
        revertSearch();
      }
    }
  };

  const isSavedSearchActive = (id: string): boolean => {
    return activeSearchId === id;
  };

  const ascendingSavedSearches = savedSearches.sort((a, b) =>
    a.name.localeCompare(b.name)
  );

  const filtersByColumn = useMemo(
    () =>
      filters.reduce(
        (allFilters, nextFilter) => ({
          ...allFilters,
          [nextFilter.field]: nextFilter.values
        }),
        {} as Record<string, string[]>
      ),
    [filters]
  );

  const noServicesFacet = facets?.['no_services']
    ? facets['no_services'][0].data.sort(
        (a: { value: string }, b: { value: string }) =>
          a.value.localeCompare(b.value)
      )
    : [];

  const portFacet: any[] = facets?.['services.port']
    ? facets['services.port'][0].data.sort(
        (a: { value: number }, b: { value: number }) => a.value - b.value
      )
    : [];

  const fromDomainFacet: any[] = facets?.['from_root_domain']
    ? facets['from_root_domain'][0].data.sort(
        (a: { value: string }, b: { value: string }) =>
          a.value.localeCompare(b.value)
      )
    : [];

  const cveFacet: any[] = facets?.['vulnerabilities.cve']
    ? facets['vulnerabilities.cve'][0].data.sort(
        (a: { value: string }, b: { value: string }) =>
          a.value.localeCompare(b.value)
      )
    : [];

  // To-Do: Create array(s) to handle permutations of null and N/A values
  const titleCaseSeverityFacet = facets?.['vulnerabilities.severity']
    ? facets['vulnerabilities.severity'][0].data.map(
        (d: { value: string; count: number }) => {
          if (d.value === null || d.value === undefined) {
            return { value: 'N/A', count: d.count };
          } else {
            return {
              value:
                d.value[0]?.toUpperCase() + d.value.slice(1)?.toLowerCase(),
              count: d.count
            };
          }
        }
      )
    : [];

  const groupedData: GroupedData = titleCaseSeverityFacet
    .map((d: SeverityData) => {
      const severityLevels = [
        'N/A',
        'Low',
        'Medium',
        'High',
        'Critical',
        'Other'
      ];
      if (severityLevels.includes(d.value)) {
        return d;
      }
      if (
        !d.value ||
        ['None', 'Null', 'N/a', 'Undefined', 'undefined'].includes(d.value)
      ) {
        return { value: 'N/A', count: d.count };
      } else {
        return { value: 'Other', count: d.count };
      }
    })
    .reduce((acc: GroupedData, curr: SeverityData) => {
      if (acc[curr.value]) {
        acc[curr.value] += curr.count;
      } else {
        acc[curr.value] = curr.count;
      }
      return acc;
    }, {});

  const sortedSeverityFacets = Object.entries(groupedData)
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => {
      const order = ['N/A', 'Low', 'Medium', 'High', 'Critical', 'Other'];
      return order.indexOf(a.value) - order.indexOf(b.value);
    });

  return (
    <Box sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}>
      <Accordion
        square
        elevation={0}
        expanded={expanded === 'panel3'}
        onChange={handleExpanded ? handleExpanded('panel3') : undefined}
        sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography variant="largeBody">IP</Typography>
            {filtersByColumn['ip']?.length > 0 && <FiltersApplied />}
          </Stack>
        </AccordionSummary>
        <AccordionDetails>
          <TaggedArrayInput
            placeholder="IP address"
            values={filtersByColumn.ip ?? []}
            onAddTag={(value) => addFilter('ip', value, 'any')}
            onRemoveTag={(value) => removeFilter('ip', value, 'any')}
          />
        </AccordionDetails>
      </Accordion>
      <Accordion
        square
        elevation={0}
        expanded={expanded === 'panel4'}
        onChange={handleExpanded ? handleExpanded('panel4') : undefined}
        sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography variant="largeBody">Domain</Typography>
            {filtersByColumn['name']?.length > 0 && <FiltersApplied />}
          </Stack>
        </AccordionSummary>
        <AccordionDetails>
          <TaggedArrayInput
            placeholder="Domain Name"
            values={filtersByColumn.name ?? []}
            onAddTag={(value) => addFilter('name', value, 'any')}
            onRemoveTag={(value) => removeFilter('name', value, 'any')}
          />
        </AccordionDetails>
      </Accordion>
      {fromDomainFacet.length > 0 && (
        <Accordion
          square
          elevation={0}
          expanded={expanded === 'panel5'}
          onChange={handleExpanded ? handleExpanded('panel5') : undefined}
          sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}
        >
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography variant="largeBody">Root Domains</Typography>
              {filtersByColumn['from_root_domain']?.length > 0 && (
                <FiltersApplied />
              )}
            </Stack>
          </AccordionSummary>
          <AccordionDetails>
            <FacetFilter
              options={fromDomainFacet}
              selected={filtersByColumn['from_root_domain'] ?? []}
              onSelect={(value) => addFilter('from_root_domain', value, 'any')}
              onDeselect={(value) =>
                removeFilter('from_root_domain', value, 'any')
              }
            />
          </AccordionDetails>
        </Accordion>
      )}
      {(portFacet.length > 0 || noServicesFacet.length > 0) && (
        <Accordion
          square
          elevation={0}
          expanded={expanded === 'panel6'}
          onChange={handleExpanded ? handleExpanded('panel6') : undefined}
          sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}
        >
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography variant="largeBody">Ports</Typography>
              {filtersByColumn['services.port']?.length > 0 ||
                (filtersByColumn['no_services']?.length > 0 && (
                  <FiltersApplied />
                ))}
            </Stack>
          </AccordionSummary>
          <AccordionDetails>
            <Stack sx={{ overflowY: 'scroll', maxHeight: '300px' }}>
              {facets.no_services &&
                facets.no_services[0].data.map((option: { count: any }) => (
                  <FormControlLabel
                    key="no_services"
                    control={
                      <Checkbox
                        sx={{
                          '&.Mui-checked': {
                            color: theme.palette.primary.dark
                          }
                        }}
                        checked={filters.some((f) => f.field === 'no_services')}
                        onChange={(e) => {
                          if (e.target.checked) {
                            addFilter('no_services', true, 'any');
                          } else {
                            removeFilter('no_services', true, 'any');
                          }
                        }}
                      />
                    }
                    label={`Unassigned`}
                  />
                ))}
              <FacetFilter
                options={portFacet}
                selected={filtersByColumn['services.port'] ?? []}
                onSelect={(value) => addFilter('services.port', value, 'any')}
                onDeselect={(value) =>
                  removeFilter('services.port', value, 'any')
                }
                disableScroll={true}
              />
            </Stack>
          </AccordionDetails>
        </Accordion>
      )}
      {cveFacet.length > 0 && (
        <Accordion
          square
          elevation={0}
          expanded={expanded === 'panel7'}
          onChange={handleExpanded ? handleExpanded('panel7') : undefined}
          sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}
        >
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography variant="largeBody">CVEs</Typography>
              {filtersByColumn['vulnerabilities.cve']?.length > 0 && (
                <FiltersApplied />
              )}
            </Stack>
          </AccordionSummary>
          <AccordionDetails>
            <FacetFilter
              options={cveFacet}
              selected={filtersByColumn['vulnerabilities.cve'] ?? []}
              onSelect={(value) =>
                addFilter('vulnerabilities.cve', value, 'any')
              }
              onDeselect={(value) =>
                removeFilter('vulnerabilities.cve', value, 'any')
              }
            />
          </AccordionDetails>
        </Accordion>
      )}
      {sortedSeverityFacets.length > 0 && (
        <Accordion
          square
          elevation={0}
          expanded={expanded === 'panel8'}
          onChange={handleExpanded ? handleExpanded('panel8') : undefined}
          sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}
        >
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography variant="largeBody">Severity</Typography>
              {filtersByColumn['vulnerabilities.severity']?.length > 0 && (
                <FiltersApplied />
              )}
            </Stack>
          </AccordionSummary>
          <AccordionDetails>
            <FacetFilter
              options={sortedSeverityFacets}
              selected={filtersByColumn['vulnerabilities.severity'] ?? []}
              onSelect={(value) =>
                addFilter('vulnerabilities.severity', value, 'any')
              }
              onDeselect={(value) =>
                removeFilter('vulnerabilities.severity', value, 'any')
              }
            />
          </AccordionDetails>
        </Accordion>
      )}
      <Accordion
        square
        elevation={0}
        expanded={expanded === 'panel9'}
        onChange={handleExpanded ? handleExpanded('panel9') : undefined}
        sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="largeBody">Saved Filters</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <SaveSearchModal
            searchTerm={searchTerm}
            filters={filters}
            totalResults={totalResults}
            sortField={''}
            sortDirection={''}
            advancedFiltersReq={advanceFiltersReq}
          />
          {ascendingSavedSearches.length > 0 ? (
            <List sx={{ maxHeight: 5 * 42, overflowY: 'auto' }}>
              {ascendingSavedSearches.map((search) => (
                <ListItem
                  key={search.id}
                  sx={{ justifyContent: 'space-between', padding: '0px' }}
                >
                  <FormGroup>
                    <FormControlLabel
                      control={
                        <Radio onClick={() => toggleSavedSearches(search.id)} />
                      }
                      label={search.name}
                      sx={{ padding: '0px' }}
                      value={search.id}
                      checked={isSavedSearchActive(search.id)}
                    />
                  </FormGroup>
                  <IconButton
                    aria-label="Delete"
                    title="Delete Search"
                    onClick={() => deleteSearch(search.id)}
                    sx={{
                      color: theme.palette.neutrals.main
                    }}
                  >
                    <DeleteOutline />
                  </IconButton>
                </ListItem>
              ))}
            </List>
          ) : (
            <List>
              <ListItem sx={{ alignItems: 'center', justifyContent: 'center' }}>
                No Saved Filters
              </ListItem>
            </List>
          )}
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export const DrawerInteriorWithSearch = withSearch(
  ({
    facets,
    searchTerm,
    setSearchTerm,
    totalResults,
    addFilter,
    removeFilter
  }: ContextType) => ({
    facets,
    searchTerm,
    setSearchTerm,
    totalResults,
    addFilter,
    removeFilter
  })
)(DrawerInterior);
