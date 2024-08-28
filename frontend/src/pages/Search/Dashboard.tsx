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
  Checkbox,
  FormControlLabel,
  FormGroup,
  TextareaAutosize,
  ButtonGroup,
  Box
} from '@mui/material';
import { Pagination } from '@mui/material';
import { withSearch } from '@elastic/react-search-ui';
import { ContextType } from '../../context/SearchProvider';
import { SortBar } from './SortBar';
import {
  Modal,
  TextInput,
  Label,
  Dropdown,
  ModalFooter,
  ModalHeading,
  ModalRef
} from '@trussworks/react-uswds';
import { ModalToggleButton } from 'components';
import { useAuthContext } from 'context';
import { FilterTags } from './FilterTags';
import { SavedSearch, Vulnerability } from 'types';
import { useBeforeunload } from 'react-beforeunload';
import { NoResults } from 'components/NoResults';
import { exportCSV } from 'components/ImportExport';
import { useHistory } from 'react-router-dom';

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
  const {
    apiPost,
    apiPut,
    setLoading,
    showAllOrganizations,
    currentOrganization
  } = useAuthContext();

  const search:
    | (SavedSearch & {
        editing?: boolean;
      })
    | undefined = localStorage.getItem('savedSearch')
    ? JSON.parse(localStorage.getItem('savedSearch')!)
    : undefined;

  const history = useHistory();
  const modalRef = useRef<ModalRef>(null);
  const [savedSearchValues, setSavedSearchValues] = useState<
    Partial<SavedSearch> & {
      name: string;
      vulnerabilityTemplate: Partial<Vulnerability>;
    }
  >(
    search
      ? search
      : {
          name: '',
          vulnerabilityTemplate: {},
          createVulnerabilities: false
        }
  );

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement
  > = (e) => onChange(e.target.name, e.target.value);

  const onChange = (name: string, value: any) => {
    setSavedSearchValues((values) => ({
      ...values,
      [name]: value
    }));
  };

  const onVulnerabilityTemplateChange = (e: any) => {
    (savedSearchValues.vulnerabilityTemplate as any)[e.target.name] =
      e.target.value;
    setSavedSearchValues(savedSearchValues);
  };

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
          <SortBar
            sortField={sortField}
            sortDirection={sortDirection}
            setSort={setSort}
            isFixed={resultsScrolled}
            saveSearch={
              filters.length > 0 || searchTerm
                ? () => modalRef.current?.toggleModal(undefined, true)
                : undefined
            }
            existingSavedSearch={search}
          />
          <Box
            height="100%"
            flexDirection="column"
            flexWrap="nowrap"
            gap="1rem"
            alignItems="stretch"
            display="flex"
            // overflow="scroll"
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

      <Modal ref={modalRef} id="modal">
        <ModalHeading>{search ? 'Update Search' : 'Save Search'}</ModalHeading>
        <FormGroup>
          <Label htmlFor="name">Name Your Search</Label>
          <TextInput
            required
            id="name"
            name="name"
            type="text"
            value={savedSearchValues.name}
            onChange={onTextChange}
          />
          <p>When a new result is found:</p>
          {/* <FormControlLabel
                  control={
                    <Checkbox
                      // checked={gilad}
                      // onChange={handleChange}
                      name="email"
                    />
                  }
                  label="Email me"
                /> */}
          <FormControlLabel
            control={
              <Checkbox
                checked={savedSearchValues.createVulnerabilities}
                onChange={(e) => onChange(e.target.name, e.target.checked)}
                id="createVulnerabilities"
                name="createVulnerabilities"
              />
            }
            label="Create a vulnerability"
          />
          {savedSearchValues.createVulnerabilities && (
            <>
              <Label htmlFor="title">Title</Label>
              <TextInput
                required
                id="title"
                name="title"
                type="text"
                value={savedSearchValues.vulnerabilityTemplate.title}
                onChange={onVulnerabilityTemplateChange}
              />
              <Label htmlFor="description">Description</Label>
              <TextareaAutosize
                required
                id="description"
                name="description"
                style={{ padding: 10 }}
                minRows={2}
                value={savedSearchValues.vulnerabilityTemplate.description}
                onChange={onVulnerabilityTemplateChange}
              />
              <Label htmlFor="description">Severity</Label>
              <Dropdown
                id="severity"
                name="severity"
                onChange={onVulnerabilityTemplateChange}
                value={
                  savedSearchValues.vulnerabilityTemplate.severity as string
                }
                style={{ display: 'inline-block', width: '150px' }}
              >
                <option value="None">None</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </Dropdown>
            </>
          )}
          {/* <h3>Collaborators</h3>
                <p>
                  Collaborators can view vulnerabilities, and domains within
                  this search. Adding a team will make all members
                  collaborators.
                </p>
                <button className={classes.addButton} >
                  <AddCircleOutline></AddCircleOutline> ADD
                </button> */}
        </FormGroup>
        <ModalFooter>
          <ButtonGroup>
            <ModalToggleButton
              modalRef={modalRef}
              closer
              onClick={async () => {
                const body = {
                  body: {
                    ...savedSearchValues,
                    searchTerm,
                    filters,
                    count: totalResults,
                    searchPath: window.location.search,
                    sortField,
                    sortDirection
                  }
                };
                if (search) {
                  await apiPut('/saved-searches/' + search.id, body);
                  history.push('/inventory');
                  window.location.reload();
                } else {
                  await apiPost('/saved-searches/', body);
                  history.push('/inventory');
                  window.location.reload();
                }
              }}
            >
              Save
            </ModalToggleButton>
            <ModalToggleButton
              modalRef={modalRef}
              closer
              unstyled
              className="padding-105 text-center"
            >
              Cancel
            </ModalToggleButton>
          </ButtonGroup>
        </ModalFooter>
      </Modal>
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
