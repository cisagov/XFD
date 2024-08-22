import React, { useEffect, useMemo, useState } from 'react';
import {
  AccordionDetails,
  Accordion as MuiAccordion,
  AccordionSummary as MuiAccordionSummary,
  IconButton,
  Paper,
  Divider,
  Stack,
  Toolbar,
  Typography,
  Box,
  Button,
  List,
  FormControlLabel,
  ListItem,
  FormGroup,
  Radio
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import {
  classes,
  StyledWrapper
} from '../pages/Search/Styling/filterDrawerStyle';
import {
  Delete,
  ExpandMore,
  FiberManualRecordRounded
} from '@mui/icons-material';
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import { SearchBar } from 'components';
import { TaggedArrayInput, FacetFilter } from 'components';
import { ContextType } from '../context/SearchProvider';
import { SavedSearch } from '../types/saved-search';
import { useAuthContext } from '../context';
import { withSearch } from '@elastic/react-search-ui';

interface Props {
  addFilter: ContextType['addFilter'];
  removeFilter: ContextType['removeFilter'];
  filters: ContextType['filters'];
  facets: ContextType['facets'];
  clearFilters: ContextType['clearFilters'];
  searchTerm: ContextType['searchTerm'];
  setSearchTerm: ContextType['setSearchTerm'];
  initialFilters: any[];
}

const FiltersApplied: React.FC = () => {
  return (
    <div className={classes.applied}>
      <FiberManualRecordRounded /> Filters Applied
    </div>
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
    clearFilters,
    searchTerm,
    setSearchTerm,
    initialFilters
  } = props;
  const { apiGet, apiDelete } = useAuthContext();
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [savedSearchCount, setSavedSearchCount] = useState(0);

  useEffect(() => {
    const fetchSearches = async () => {
      try {
        const response = await apiGet('/saved-searches');
        setSavedSearches(response.result);
        setSavedSearchCount(response.result.length);
      } catch (error) {
        console.error('Error fetching searches:', error);
      }
    };
    fetchSearches();
  }, [apiGet]);

  const deleteSearch = async (id: string) => {
    try {
      await apiDelete(`/saved-searches/${id}`, { body: {} });
      const updatedSearches = await apiGet('/saved-searches'); // Get current saved searches
      setSavedSearches(updatedSearches.result); // Update the saved searches
      setSavedSearchCount(updatedSearches.result.length); // Update the count
    } catch (e) {
      console.log(e);
    }
  };
  const displaySavedSearch = (id: string) => {
    const savedSearch = savedSearches.find((search) => search.id === id);
    if (savedSearch) {
      localStorage.setItem('savedSearch', JSON.stringify(savedSearch));
      setSearchTerm(savedSearch.searchTerm, {
        shouldClearFilters: true,
        autocompleteResults: false
      });
    }

    savedSearch?.filters?.forEach((filter) => {
      filter.values.forEach((value) => {
        addFilter(filter.field, value, 'any');
      });
    });
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
    localStorage.removeItem('savedSearch');
    restoreInitialFilters();
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

  const isSavedSearchActive = (id: string) => {
    const activeSearch = JSON.parse(
      localStorage.getItem('savedSearch') || '{}'
    );
    return activeSearch.id === id;
  };

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

  const portFacet: any[] = facets['services.port']
    ? facets['services.port'][0].data
    : [];

  const fromDomainFacet: any[] = facets['fromRootDomain']
    ? facets['fromRootDomain'][0].data
    : [];

  const cveFacet: any[] = facets['vulnerabilities.cve']
    ? facets['vulnerabilities.cve'][0].data
    : [];

  const severityFacet: any[] = facets['vulnerabilities.severity']
    ? facets['vulnerabilities.severity'][0].data
    : [];

  // Always show all severities
  for (const value of ['Critical', 'High', 'Medium', 'Low']) {
    if (!severityFacet.find((severity) => value === severity.value))
      severityFacet.push({ value, count: 0 });
  }

  return (
    <StyledWrapper style={{ overflowY: 'auto' }}>
      <Toolbar sx={{ justifyContent: 'center' }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography variant="h6" component="h3">
            Advanced Filters
          </Typography>
          <FilterAltIcon />
        </Stack>
      </Toolbar>
      <Divider />
      <div className={classes.header}>
        <SearchBar
          initialValue={searchTerm}
          value={searchTerm}
          onChange={(value) => {
            setSearchTerm(value, {
              shouldClearFilters: false,
              autocompleteResults: false
            });
          }}
        />
      </div>
      {clearFilters && (
        <Box display="flex" width="100%" justifyContent="center">
          <Button onClick={clearFilters}>Clear All Filters</Button>
        </Box>
      )}
      <Accordion
        sx={{
          marginTop: 1
        }}
        elevation={0}
        square
        classes={{
          root: classes.root,
          disabled: classes.disabled,
          expanded: classes.expanded
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMore />}
          classes={{
            root: classes.root2,
            content: classes.content,
            disabled: classes.disabled2,
            expanded: classes.expanded2
          }}
        >
          <div>IP(s)</div>
          {filtersByColumn['ip']?.length > 0 && <FiltersApplied />}
        </AccordionSummary>
        <AccordionDetails classes={{ root: classes.details }}>
          <TaggedArrayInput
            placeholder="IP address"
            values={filtersByColumn.ip ?? []}
            onAddTag={(value) => addFilter('ip', value, 'any')}
            onRemoveTag={(value) => removeFilter('ip', value, 'any')}
          />
        </AccordionDetails>
      </Accordion>
      <Accordion
        elevation={0}
        square
        classes={{
          root: classes.root,
          disabled: classes.disabled,
          expanded: classes.expanded
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMore />}
          classes={{
            root: classes.root2,
            content: classes.content,
            disabled: classes.disabled2,
            expanded: classes.expanded2
          }}
        >
          <div>Domain(s)</div>
          {filtersByColumn['name']?.length > 0 && <FiltersApplied />}
        </AccordionSummary>
        <AccordionDetails classes={{ root: classes.details }}>
          <TaggedArrayInput
            placeholder="Domain"
            values={filtersByColumn.name ?? []}
            onAddTag={(value) => addFilter('name', value, 'any')}
            onRemoveTag={(value) => removeFilter('name', value, 'any')}
          />
        </AccordionDetails>
      </Accordion>
      {fromDomainFacet.length > 0 && (
        <Accordion
          elevation={0}
          square
          classes={{
            root: classes.root,
            disabled: classes.disabled,
            expanded: classes.expanded
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMore />}
            classes={{
              root: classes.root2,
              content: classes.content,
              disabled: classes.disabled2,
              expanded: classes.expanded2
            }}
          >
            <div>Root Domain(s)</div>
            {filtersByColumn['fromRootDomain']?.length > 0 && (
              <FiltersApplied />
            )}
          </AccordionSummary>
          <AccordionDetails classes={{ root: classes.details }}>
            <FacetFilter
              options={fromDomainFacet}
              selected={filtersByColumn['fromRootDomain'] ?? []}
              onSelect={(value) => addFilter('fromRootDomain', value, 'any')}
              onDeselect={(value) =>
                removeFilter('fromRootDomain', value, 'any')
              }
            />
          </AccordionDetails>
        </Accordion>
      )}
      {portFacet.length > 0 && (
        <Accordion
          elevation={0}
          square
          classes={{
            root: classes.root,
            disabled: classes.disabled,
            expanded: classes.expanded
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMore />}
            classes={{
              root: classes.root2,
              content: classes.content,
              disabled: classes.disabled2,
              expanded: classes.expanded2
            }}
          >
            <div>Port(s)</div>
            {filtersByColumn['services.port']?.length > 0 && <FiltersApplied />}
          </AccordionSummary>
          <AccordionDetails classes={{ root: classes.details }}>
            <FacetFilter
              options={portFacet}
              selected={filtersByColumn['services.port'] ?? []}
              onSelect={(value) => addFilter('services.port', value, 'any')}
              onDeselect={(value) =>
                removeFilter('services.port', value, 'any')
              }
            />
          </AccordionDetails>
        </Accordion>
      )}
      {cveFacet.length > 0 && (
        <Accordion
          elevation={0}
          square
          classes={{
            root: classes.root,
            disabled: classes.disabled,
            expanded: classes.expanded
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMore />}
            classes={{
              root: classes.root2,
              content: classes.content,
              disabled: classes.disabled2,
              expanded: classes.expanded2
            }}
          >
            <div>CVE(s)</div>
            {filtersByColumn['vulnerabilities.cve']?.length > 0 && (
              <FiltersApplied />
            )}
          </AccordionSummary>
          <AccordionDetails classes={{ root: classes.details }}>
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
      {severityFacet.length > 0 && (
        <Accordion
          elevation={0}
          square
          classes={{
            root: classes.root,
            disabled: classes.disabled,
            expanded: classes.expanded
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMore />}
            classes={{
              root: classes.root2,
              content: classes.content,
              disabled: classes.disabled2,
              expanded: classes.expanded2
            }}
          >
            <div>Severity</div>
            {filtersByColumn['vulnerabilities.severity']?.length > 0 && (
              <FiltersApplied />
            )}
          </AccordionSummary>
          <AccordionDetails classes={{ root: classes.details }}>
            <FacetFilter
              options={severityFacet}
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
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>Saved Searches</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            {savedSearches.map((search) => (
              <ListItem
                key={search.id}
                sx={{ justifyContent: 'space-between', padding: '0px' }}
              >
                <FormGroup>
                  <FormControlLabel
                    control={<Radio />}
                    label={search.name}
                    sx={{ padding: '0px' }}
                    value={search.id}
                    onClick={() => toggleSavedSearches(search.id)}
                    checked={isSavedSearchActive(search.id)}
                  />
                </FormGroup>
                <IconButton
                  aria-label="Delete"
                  title="Delete Search"
                  onClick={() => deleteSearch(search.id)}
                >
                  <Delete />
                </IconButton>
              </ListItem>
            ))}
          </List>
          <Paper elevation={2} style={{ width: '15em' }}>
            {savedSearches.length > 0 ? (
              <DataGrid
                density="compact"
                key={'Data Grid'}
                rows={savedSearches.map((search) => ({ ...search }))}
                rowCount={savedSearchCount}
                columns={[
                  {
                    field: 'name',
                    headerName: 'Name',
                    flex: 1,
                    width: 100,
                    description: 'Name',
                    renderCell: (cellValues) => {
                      const applyFilter = () => {
                        // if (clearFilters) clearFilters();
                        localStorage.setItem(
                          'savedSearch',
                          JSON.stringify(cellValues.row)
                        );
                        setSearchTerm(cellValues.row.searchTerm, {
                          shouldClearFilters: false,
                          autocompleteResults: false
                        });

                        // Apply the filters
                        cellValues.row.filters.forEach((filter) => {
                          filter.values.forEach((value) => {
                            addFilter(filter.field, value, 'any');
                          });
                        });
                      };
                      return (
                        <div
                          aria-label={cellValues.row.name}
                          title={`Saved Search: ${cellValues.row.name}`}
                          tabIndex={0}
                          onClick={applyFilter}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              applyFilter();
                            }
                          }}
                          style={{
                            cursor: 'pointer',
                            textAlign: 'left',
                            width: '100%'
                          }}
                        >
                          {cellValues.value}
                        </div>
                      );
                    }
                  },
                  {
                    field: 'actions',
                    headerName: '',
                    flex: 0.1,
                    renderCell: (cellValues) => {
                      const searchId = cellValues.id.toString();
                      return (
                        <div style={{ display: 'flexbox', textAlign: 'end' }}>
                          <IconButton
                            aria-label="Delete"
                            title="Delete Search"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteSearch(searchId);
                            }}
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                deleteSearch(searchId);
                              }
                            }}
                          >
                            <Delete />
                          </IconButton>
                        </div>
                      );
                    }
                  }
                ]}
                initialState={{
                  pagination: {
                    paginationModel: {
                      pageSize: 5
                    }
                  }
                }}
                pageSizeOptions={[5, 10]}
                disableRowSelectionOnClick
                sx={{
                  disableColumnfilter: 'true',
                  '& .MuiDataGrid-row:hover': {
                    cursor: 'pointer'
                  }
                }}
              />
            ) : (
              <div>No Saved Searches</div>
            )}
          </Paper>
        </AccordionDetails>
        {/* </Accordion> */}
      </Accordion>
    </StyledWrapper>
  );
};

export const DrawerInteriorWithSearch = withSearch(
  ({ searchTerm, setSearchTerm }: ContextType) => ({
    searchTerm,
    setSearchTerm
  })
)(DrawerInterior);
