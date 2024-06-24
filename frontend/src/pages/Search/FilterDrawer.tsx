import React, { useEffect, useMemo, useState, useRef } from 'react';
import {
  AccordionDetails,
  Accordion as MuiAccordion,
  AccordionSummary as MuiAccordionSummary,
  Button
} from '@mui/material';
import { classes, StyledWrapper } from './Styling/filterDrawerStyle';
import {
  Edit,
  Delete,
  ExpandMore,
  FiberManualRecordRounded
} from '@mui/icons-material';
import { FaFilter } from 'react-icons/fa';
import { TaggedArrayInput, FacetFilter } from 'components';
import { ContextType } from '../../context/SearchProvider';
import { SavedSearch } from '../../types/saved-search';
import { useAuthContext } from '../../context';
import { useHistory } from 'react-router-dom';

interface Props {
  addFilter: ContextType['addFilter'];
  removeFilter: ContextType['removeFilter'];
  filters: ContextType['filters'];
  facets: ContextType['facets'];
  clearFilters: ContextType['clearFilters'];
  updateSearchTerm: (term: string) => void;
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

export const FilterDrawer: React.FC<Props> = (props) => {
  const { filters, addFilter, removeFilter, facets, clearFilters } = props;
  const { apiGet, apiDelete } = useAuthContext();
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const history = useHistory();

  const loadSearches = () => {
    return apiGet('/saved-searches');
  };

  useEffect(() => {
    const fetchSearches = async () => {
      // const response = await apiGet('/saved-searches');
      try {
        const response = await loadSearches();
        setSavedSearches(response.result);
      } catch (error) {
        console.error('Error fetching searches:', error);
      }
    };

    fetchSearches();
  }, []);

  const deleteSearch = async (id: string) => {
    try {
      await apiDelete(`/saved-searches/${id}`, { body: {} });
      setSavedSearches(savedSearches.filter((search) => search.id !== id));
    } catch (e) {
      console.log(e);
    }
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
      <div className={classes.header}>
        <div className={classes.filter}>
          <FaFilter /> <h3>Filter</h3>
        </div>
        {clearFilters && (
          <div>
            <button onClick={clearFilters}>Clear All Filters</button>
          </div>
        )}
      </div>
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
          <h3>Saved Searches</h3>
        </AccordionSummary>
        <Accordion style={{ overflowY: 'auto' }}>
          <AccordionDetails classes={{ root: classes.details }}>
            {savedSearches.map((search) => (
              <div key={search.id}>
                {
                  <Button
                    onClick={() => {
                      if (clearFilters) clearFilters();
                      console.log('bbb');
                      localStorage.setItem(
                        'savedSearch',
                        JSON.stringify(search)
                      );
                      history.push(
                        '/inventory' +
                          search.searchPath +
                          '&searchId=' +
                          search.id
                      );
                      props.updateSearchTerm(search.searchTerm);
                      console.log(
                        JSON.parse(localStorage.getItem('savedSearch')!)
                      );
                      // Apply the filters
                      search.filters.forEach((filter) => {
                        // console.log('Filter: ', filter);
                        filter.values.forEach((value) => {
                          // console.log(
                          //   'Filter Field: ',
                          //   filter.field,
                          //   'Value: ',
                          //   value
                          // );
                          addFilter(filter.field, value, 'any');
                        });
                      });
                    }}
                    key={search.id}
                    style={{ textDecoration: 'none' }}
                  >
                    <p className={classes.savedSearchText}>{search.name}</p>
                  </Button>
                }
                <a
                  style={{
                    cursor: 'pointer'
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    console.log('CLICKED!');
                  }}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      console.log('CLICKED with keyboard!');
                    }
                  }}
                >
                  <Edit />
                </a>
                <a
                  onClick={() => deleteSearch(search.id)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      deleteSearch(search.id);
                    }
                  }}
                >
                  <Delete />
                </a>

                {/* <p>Created At: {search.createdAt}</p>
                <p>Updated At: {search.updatedAt}</p>
                <p>Search Term: {search.searchTerm}</p>
                <p>Count: {search.count}</p>
                <p>Search Path: {search.searchPath}</p> */}
              </div>
            ))}
          </AccordionDetails>
        </Accordion>
      </Accordion>
    </StyledWrapper>
  );
};
