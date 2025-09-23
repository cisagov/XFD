import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { useAuthContext } from 'context';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Autocomplete,
  Button,
  Checkbox,
  FormControlLabel,
  FormGroup,
  List,
  ListItem,
  TextField,
  Typography,
  useTheme
} from '@mui/material';
import { useStaticsContext } from 'context/StaticsContext';
import {
  ORGANIZATION_EXCLUSIONS
  // REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS
} from 'hooks/useUserTypeFilters';
import { ExpandMore, FiberManualRecordRounded } from '@mui/icons-material';
import {
  useUserLevel,
  GLOBAL_ADMIN,
  GLOBAL_VIEW,
  REGIONAL_ADMIN,
  STANDARD_USER
} from 'hooks/useUserLevel';
import { Stack } from '@mui/system';
// import { GLOBAL_VIEW } from '@/context/userStateUtils';

// const GLOBAL_ADMIN = 3;
// const STANDARD_USER = 1;

// Swap this value to allow regional admin to filter on regions that aren't their own
export const toggleRegionalUserType = true;

export const REGION_FILTER_KEY = 'organization.region_id';
export const ORGANIZATION_FILTER_KEY = 'organization_id';

export interface OrganizationShallow {
  region_id: string;
  name: string;
  id: string;
  root_domains: string[];
}

interface RegionAndOrganizationFiltersProps {
  addFilter: (
    name: string,
    value: any,
    filterType: 'all' | 'any' | 'none'
  ) => void;
  removeFilter: (
    name: string,
    value: any,
    filterType: 'all' | 'any' | 'none'
  ) => void;
  filters: any[];
  setSearchTerm: (s: string, opts?: any) => void;
  searchTerm: string;
  autocompletedResults: any[];
  autocompletedSuggestions: any;
  results: any[];
  initialFilters: any[];
  expanded?: string | false;

  handleExpanded?: (
    panel: string
  ) => (event: React.SyntheticEvent, newExpanded: boolean) => void;
}

const FiltersApplied: React.FC = () => {
  const theme = useTheme();
  return (
    <FiberManualRecordRounded
      sx={{ color: theme.palette.primary.main, height: '1rem', width: '1rem' }}
    />
  );
};

export const RegionAndOrganizationFilters: React.FC<
  RegionAndOrganizationFiltersProps
> = ({
  addFilter,
  removeFilter,
  filters,
  initialFilters,
  expanded,

  handleExpanded
}) => {
  const { setShowMaps, user, apiPost } = useAuthContext();
  const { regions } = useStaticsContext();
  const [search_term, setSearchTerm] = useState<string>('');
  const [orgResults, setOrgResults] = useState<OrganizationShallow[]>([]);
  const [isOrgOpen, setIsOrgOpen] = useState(false);
  const [isRegOpen, setIsRegOpen] = useState(false);
  const userLevel = useUserLevel().userLevel;
  const theme = useTheme();

  const searchOrganizations = useCallback(
    async (search_term: string, regions?: string[]) => {
      try {
        const results = await apiPost<{
          body: { hits: { hits: { _source: OrganizationShallow }[] } };
        }>('/search/organizations', {
          body: {
            search_term,
            regions
          }
        });

        const orgs = results.body.hits.hits.map((hit) => hit._source);
        // Filter out organizations that match the exclusions
        const refinedOrgs = orgs.filter((org) => {
          let exlude = false;
          ORGANIZATION_EXCLUSIONS.forEach((exc) => {
            if (org.name.toLowerCase().includes(exc)) {
              exlude = true;
            }
          });
          return !exlude;
        });
        // Filter out organizations that are already in the filters
        const filteredOrgs = refinedOrgs.filter(
          (org) =>
            !filters.find(
              (filter) =>
                filter.field === ORGANIZATION_FILTER_KEY &&
                filter.values.find(
                  (value: { id: string }) => value.id === org.id
                )
            )
        );
        // Sort filtered orgs by name
        const sortedOrgs = filteredOrgs.sort((a, b) =>
          a.name.localeCompare(b.name)
        );

        // Utility function to replce HTML encodings
        const decodeHtml = (org_name: string): string => {
          const encodings: { [key: string]: string } = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#039;': "'"
          };
          return org_name.replace(/&amp;|&lt;|&gt;|&quot;|&#039;/g, (m) => {
            return encodings[m];
          });
        };
        // Decode HTML encodings in org names
        sortedOrgs.forEach((org) => {
          org.name = decodeHtml(org.name);
        });

        setOrgResults(sortedOrgs);
      } catch (e) {
        console.log(e);
      }
    },
    [apiPost, setOrgResults, filters]
  );

  const regionFilterValues = useMemo(() => {
    const regionFilter = filters.find(
      (filter) => filter.field === REGION_FILTER_KEY
    );

    if (regionFilter !== undefined) {
      return regionFilter.values as string[];
    }
    return null;
  }, [filters]);

  const handleCheckboxChange = (region_id: string) => {
    if (allRegionsSelected) {
      regions.forEach((region) => {
        removeFilter(REGION_FILTER_KEY, region, 'any');
      });
      addFilter(REGION_FILTER_KEY, region_id, 'any');
      return;
    }
    if (!allRegionsSelected && regionFilterValues?.includes(region_id)) {
      removeFilter(REGION_FILTER_KEY, region_id, 'any');
    } else {
      addFilter(REGION_FILTER_KEY, region_id, 'any');
    }
  };

  const handleTextChange = (v: string) => {
    setSearchTerm(v);
  };

  const organizationsInFilters = useMemo(() => {
    const orgsFilter = filters.find(
      (filter) => filter.field === ORGANIZATION_FILTER_KEY
    );
    if (orgsFilter !== undefined) {
      return orgsFilter.values as OrganizationShallow[];
    } else {
      return null;
    }
  }, [filters]);

  useEffect(() => {
    searchOrganizations(search_term, regionFilterValues ?? []);
  }, [searchOrganizations, search_term, regionFilterValues]);

  useEffect(() => {
    if (organizationsInFilters && regionFilterValues) {
      organizationsInFilters.forEach((org) => {
        if (!regionFilterValues.includes(org.region_id)) {
          removeFilter(ORGANIZATION_FILTER_KEY, org, 'any');
        }
      });
    }
  }, [organizationsInFilters, regionFilterValues, removeFilter]);

  const userOrg = user?.roles?.map((role) => role.organization.name);

  const allRegionsSelected = useMemo(() => {
    return (
      regionFilterValues?.length === regions.length ||
      ((userLevel === GLOBAL_ADMIN || userLevel === GLOBAL_VIEW) &&
        regionFilterValues?.length === 0)
    );
  }, [regionFilterValues, regions.length, userLevel]);

  const regionExistsInFilters = useCallback(
    (region_id: string) => {
      return regionFilterValues?.includes(region_id);
    },
    [regionFilterValues]
  );
  const handleAddOrganization = (org: OrganizationShallow) => {
    if (org) {
      const exists = organizationsInFilters?.find((o) => o.id === org.id);
      if (exists) {
        removeFilter(ORGANIZATION_FILTER_KEY, org, 'any');
      } else {
        addFilter(ORGANIZATION_FILTER_KEY, org, 'any');
      }
      setSearchTerm('');
      setIsOrgOpen(false);
      if (org.name === 'Election') {
        setShowMaps(true);
      } else {
        setShowMaps(false);
      }
    }
  };

  const restoreInitialFilters = () => {
    initialFilters.forEach((filter) => {
      filter.values.forEach((value: string) => {
        addFilter(filter.field, value, 'any');
      });
    });
  };

  const nonInitialFilters = filters.filter((currentFilter) => {
    const initial = initialFilters.find(
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

  const nonInitialRegionFilter = nonInitialFilters.find(
    (filter) => filter.field === REGION_FILTER_KEY
  );

  const nonInitialOrgFilter = nonInitialFilters.find(
    (filter) => filter.field === ORGANIZATION_FILTER_KEY
  );

  return (
    <>
      <Accordion
        square
        elevation={0}
        expanded={expanded === 'panel1'}
        onChange={handleExpanded ? handleExpanded('panel1') : undefined}
        disableGutters
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography variant="largeBody">Regions</Typography>
            {nonInitialRegionFilter?.values.length > 0 && <FiltersApplied />}
          </Stack>
        </AccordionSummary>
        <AccordionDetails>
          {userLevel !== GLOBAL_ADMIN && userLevel !== GLOBAL_VIEW && (
            <Autocomplete
              onInputChange={(e, v) => {
                if (e && e.type === 'change') {
                  handleTextChange(v);
                }
              }}
              disableClearable
              disabled={
                !userLevel ||
                (userLevel !== GLOBAL_ADMIN && userLevel !== GLOBAL_VIEW)
              }
              open={isRegOpen}
              onOpen={() => {
                setIsRegOpen(true);
              }}
              options={regions}
              onChange={(e, v) => {
                setTimeout(() => {
                  handleCheckboxChange(v);
                }, 250);
                return;
              }}
              getOptionLabel={(option) => `Region ${option}`}
              slotProps={{
                listbox: {
                  sx: {
                    ':active': {
                      bgcolor: 'transparent'
                    },
                    overflow: 'auto',
                    overscrollBehavior: 'contain'
                  }
                }
              }}
              renderOption={(params, option) => {
                return (
                  <li
                    {...params}
                    style={{ pointerEvents: 'none', padding: 0 }}
                    key={`region-filter-item-${option}`}
                  >
                    <Button
                      sx={{
                        pointerEvents: 'auto',
                        height: '100%',
                        width: '100%',
                        display: 'flex',
                        textAlign: 'left',
                        justifyContent: 'start',
                        fontWeight: 400,
                        color: 'black',
                        textTransform: 'none'
                      }}
                      id="search-region-button"
                      onClick={() =>
                        setTimeout(() => {
                          handleCheckboxChange(option);
                        }, 250)
                      }
                    >
                      {`Region ${option}`}
                    </Button>
                  </li>
                );
              }}
              isOptionEqualToValue={(option, value) => option === value}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label={
                    userLevel === GLOBAL_ADMIN || userLevel === GLOBAL_VIEW
                      ? 'All Regions'
                      : `Region ${user?.region_id}`
                  }
                  value={search_term}
                  onBlur={() => setIsRegOpen(false)}
                  placeholder={
                    organizationsInFilters
                      ? `Region${organizationsInFilters[0].region_id}`
                      : 'All Regions'
                  }
                />
              )}
            />
          )}
          {(userLevel === GLOBAL_ADMIN || userLevel === GLOBAL_VIEW) && (
            <List sx={{ maxHeight: 5 * 42, overflowY: 'auto' }}>
              <ListItem
                sx={{ padding: '0px' }}
                key={`region-filter-item-all-regions`}
              >
                <FormGroup>
                  <FormControlLabel
                    control={
                      <Checkbox
                        sx={{
                          '&.Mui-checked': {
                            color: theme.palette.primary.dark
                          }
                        }}
                      />
                    }
                    label={`All Regions`}
                    checked={allRegionsSelected}
                    onChange={() => {
                      if (allRegionsSelected) {
                        regions.forEach((region) => {
                          removeFilter(REGION_FILTER_KEY, region, 'any');
                        });
                      } else {
                        restoreInitialFilters();
                      }
                    }}
                    sx={{ padding: '0px' }}
                  />
                </FormGroup>
              </ListItem>
              {(userLevel === GLOBAL_ADMIN || userLevel === GLOBAL_VIEW) &&
                regions.map((region) => {
                  return (
                    <RegionItem
                      key={`region-item-${region}`}
                      handleChange={handleCheckboxChange}
                      region_id={region}
                      checked={
                        (regionExistsInFilters(region) &&
                          !allRegionsSelected) ??
                        false
                      }
                    />
                  );
                })}
            </List>
          )}
          {(userLevel === GLOBAL_ADMIN || userLevel === GLOBAL_VIEW) && (
            <div
              style={{
                position: 'relative',
                width: '100%',
                height: 0
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  right: 0,
                  bottom: 0,
                  height: 24,
                  pointerEvents: 'none',
                  background:
                    'linear-gradient(to bottom, rgba(255,255,255,0), #fff 90%)'
                }}
              />
            </div>
          )}
        </AccordionDetails>
      </Accordion>

      {/* Need to reconcile type issues caused by adding freeSolo prop */}

      <Accordion
        square
        elevation={0}
        expanded={expanded === 'panel2'}
        onChange={handleExpanded ? handleExpanded('panel2') : undefined}
        sx={{ borderTop: `.5px solid ${theme.palette.neutrals.light}` }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Typography variant="largeBody">Organizations</Typography>
            {nonInitialOrgFilter?.values.length > 0 && <FiltersApplied />}
          </Stack>
        </AccordionSummary>
        <AccordionDetails>
          <Autocomplete
            onInputChange={(e, v) => {
              if (e && e.type === 'change') {
                handleTextChange(v);
              }
            }}
            inputValue={search_term}
            // freeSolo
            disableClearable
            disabled={userLevel === STANDARD_USER}
            open={isOrgOpen}
            onOpen={() => {
              setIsOrgOpen(true);
            }}
            options={orgResults}
            onChange={(e, v) => {
              setTimeout(() => {
                handleAddOrganization(v);
              }, 250);
              return;
            }}
            getOptionLabel={(option) => option.name}
            slotProps={{
              listbox: {
                sx: {
                  ':active': {
                    bgcolor: 'transparent'
                  },
                  overflow: 'auto',
                  overscrollBehavior: 'contain'
                }
              }
            }}
            renderOption={(params, option) => {
              return (
                <li
                  {...params}
                  style={{ pointerEvents: 'none', padding: 0 }}
                  key={option.id}
                >
                  <Button
                    sx={{
                      pointerEvents: 'auto',
                      height: '100%',
                      width: '100%',
                      display: 'flex',
                      textAlign: 'left',
                      justifyContent: 'start',
                      fontWeight: 400,
                      color: 'black',
                      textTransform: 'none'
                    }}
                    id="search-org-button"
                    onClick={() =>
                      setTimeout(() => {
                        handleAddOrganization(option);
                      }, 250)
                    }
                  >
                    {option.name}
                  </Button>
                </li>
              );
            }}
            isOptionEqualToValue={(option, value) =>
              option?.name === value?.name
            }
            renderInput={(params) => (
              <TextField
                {...params}
                label={
                  userLevel !== STANDARD_USER
                    ? 'Search Organizations'
                    : `${userOrg}`
                }
                onBlur={() => setIsOrgOpen(false)}
                helperText={
                  userLevel === REGIONAL_ADMIN ||
                  userLevel === GLOBAL_ADMIN ||
                  userLevel === GLOBAL_VIEW
                    ? 'This search shows up to 10 organizations to start. Begin typing to search across all organizations and select one.'
                    : ''
                }
              />
            )}
          />
          {userLevel !== STANDARD_USER && (
            <List sx={{ width: '100%', maxHeight: 5 * 42, overflowY: 'auto' }}>
              {organizationsInFilters?.map((org) => {
                return (
                  <ListItem key={org.id} sx={{ padding: '0px' }}>
                    <FormGroup>
                      <FormControlLabel
                        sx={{ padding: '0px' }}
                        label={<OrgCheckboxLabel org={org} />}
                        control={
                          <Checkbox
                            sx={{
                              '&.Mui-checked': {
                                color: theme.palette.primary.dark
                              }
                            }}
                          />
                        }
                        checked={true}
                        onChange={() => {
                          const exists = organizationsInFilters.find(
                            (organization) => organization.id === org.id
                          );
                          if (exists) {
                            removeFilter(ORGANIZATION_FILTER_KEY, org, 'any');
                          } else {
                            addFilter(ORGANIZATION_FILTER_KEY, org, 'any');
                          }
                        }}
                      />
                    </FormGroup>
                  </ListItem>
                );
              })}
            </List>
          )}
        </AccordionDetails>
      </Accordion>
    </>
  );
};

interface RegionItemProps {
  region_id: string;
  handleChange: (region_id: string) => void;
  checked: boolean;
  disabled?: boolean;
}

const RegionItem: React.FC<RegionItemProps> = ({
  region_id: region,
  handleChange,
  checked,
  disabled = false
}) => {
  const theme = useTheme();
  return (
    <ListItem sx={{ padding: '0px' }} key={`region-filter-item-${region}`}>
      <FormGroup>
        <FormControlLabel
          control={
            <Checkbox
              sx={{
                '&.Mui-checked': {
                  color: theme.palette.primary.dark
                }
              }}
            />
          }
          label={`Region ${region}`}
          checked={checked}
          disabled={disabled}
          onChange={() => {
            handleChange(region);
          }}
          sx={{ padding: '0px' }}
        />
      </FormGroup>
    </ListItem>
  );
};

interface OrganizationCheckboxLabelProps {
  org: OrganizationShallow;
}
const OrgCheckboxLabel: React.FC<OrganizationCheckboxLabelProps> = ({
  org
}) => {
  return (
    <>
      <Typography variant="body1">{org.name}</Typography>
      <Typography variant="uiElementsIII">{`Region ${org.region_id}`}</Typography>
    </>
  );
};
