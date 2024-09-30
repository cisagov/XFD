import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { useAuthContext } from 'context';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  FormGroup,
  List,
  ListItem,
  TextField,
  Typography
} from '@mui/material';
import { ExpandMore } from '@mui/icons-material';
import { useStaticsContext } from 'context/StaticsContext';
import {
  ORGANIZATION_EXCLUSIONS,
  REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS
} from 'hooks/useUserTypeFilters';
import { SearchBar } from './SearchBar';
import { useHistory, useLocation } from 'react-router-dom';

const GLOBAL_ADMIN = 3;
const REGIONAL_ADMIN = 2;
const STANDARD_USER = 1;

// Swap this value to allow regional admin to filter on regions that aren't their own
export const toggleRegionalUserType = true;

export const REGION_FILTER_KEY = 'organization.regionId';
export const ORGANIZATION_FILTER_KEY = 'organizationId';

export interface OrganizationShallow {
  regionId: string;
  name: string;
  id: string;
  rootDomains: string[];
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
}

export const RegionAndOrganizationFilters: React.FC<
  RegionAndOrganizationFiltersProps
> = ({
  addFilter,
  removeFilter,
  filters,
  searchTerm: domainSearchTerm,
  setSearchTerm: setDomainSearchTerm
}) => {
  const { setShowMaps, user, apiPost } = useAuthContext();

  const { regions } = useStaticsContext();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [orgResults, setOrgResults] = useState<OrganizationShallow[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  let userLevel = 0;
  if (user && user.isRegistered) {
    if (user.userType === 'standard') {
      userLevel = STANDARD_USER;
    } else if (user.userType === 'globalAdmin') {
      userLevel = GLOBAL_ADMIN;
    } else if (
      user.userType === 'regionalAdmin' ||
      user.userType === 'globalView'
    ) {
      userLevel = REGIONAL_ADMIN;
    }
  }
  const searchOrganizations = useCallback(
    async (searchTerm: string, regions?: string[]) => {
      try {
        const results = await apiPost<{
          body: { hits: { hits: { _source: OrganizationShallow }[] } };
        }>('/search/organizations', {
          body: {
            searchTerm,
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
        setOrgResults(filteredOrgs);
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

  const handleCheckboxChange = (regionId: string) => {
    if (regionFilterValues?.includes(regionId)) {
      removeFilter(REGION_FILTER_KEY, regionId, 'any');
    } else {
      addFilter(REGION_FILTER_KEY, regionId, 'any');
    }
  };

  const handleTextChange = (v: string) => {
    setSearchTerm(v);
  };

  useEffect(() => {
    searchOrganizations(searchTerm, regionFilterValues ?? []);
  }, [searchOrganizations, searchTerm, regionFilterValues]);

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

  const showUsersRegionDisabled = useMemo(() => {
    return (
      (userLevel === STANDARD_USER ||
        (!REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS &&
          userLevel !== GLOBAL_ADMIN)) &&
      user?.regionId
    );
  }, [user?.regionId, userLevel]);

  const regionExistsInFilters = useCallback(
    (regionId: string) => {
      return regionFilterValues?.includes(regionId);
    },
    [regionFilterValues]
  );
  const history = useHistory();
  const location = useLocation();

  const handleAddOrganization = (org: OrganizationShallow) => {
    if (org) {
      const exists = organizationsInFilters?.find((o) => o.id === org.id);
      if (exists) {
        removeFilter(ORGANIZATION_FILTER_KEY, org, 'any');
      } else {
        addFilter(ORGANIZATION_FILTER_KEY, org, 'any');
      }
      setSearchTerm('');
      setIsOpen(false);
      if (org.name === 'Election') {
        setShowMaps(true);
      } else {
        setShowMaps(false);
      }
    } else {
    }
  };

  return (
    <>
      <Divider />
      <Box padding={2}>
        <SearchBar
          initialValue={domainSearchTerm}
          value={domainSearchTerm}
          onChange={(value) => {
            if (location.pathname !== '/inventory') {
              history.push(`/inventory?q=${value}`);
              setDomainSearchTerm(value, {
                shouldClearFilters: false,
                refresh: true
              });
            }
            setDomainSearchTerm(value, {
              shouldClearFilters: false
            });
          }}
        />
      </Box>
      <Accordion
        expanded={userLevel === STANDARD_USER ? true : undefined}
        defaultExpanded
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>Region(s)</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            {showUsersRegionDisabled && user?.regionId ? (
              <ListItem sx={{ padding: '0px' }} key={user?.regionId}>
                <FormGroup>
                  <FormControlLabel
                    control={<Checkbox />}
                    disabled={true}
                    label={`Region ${user?.regionId}`}
                    checked={true}
                    sx={{ padding: '0px' }}
                  />
                </FormGroup>
              </ListItem>
            ) : (
              regions.map((region) => {
                return (
                  <RegionItem
                    key={`region-item-${region}`}
                    handleChange={handleCheckboxChange}
                    regionId={region}
                    checked={regionExistsInFilters(region) ?? false}
                  />
                );
              })
            )}
          </List>
        </AccordionDetails>
      </Accordion>
      <Accordion
        defaultExpanded
        expanded={userLevel === STANDARD_USER ? true : undefined}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>Organization(s)</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {/* Need to reconcile type issues caused by adding freeSolo prop */}
          {userLevel !== STANDARD_USER ? (
            <Autocomplete
              onInputChange={(e, v) => {
                if (e && e.type === 'change') {
                  handleTextChange(v);
                }
              }}
              inputValue={searchTerm}
              // freeSolo
              disableClearable
              open={isOpen}
              onOpen={() => {
                setIsOpen(true);
              }}
              options={orgResults}
              onChange={(e, v) => {
                setTimeout(() => {
                  handleAddOrganization(v);
                }, 250);
                return;
              }}
              getOptionLabel={(option) => option.name}
              ListboxProps={{
                sx: {
                  ':active': {
                    bgcolor: 'transparent'
                  }
                }
              }}
              renderOption={(params, option) => {
                return (
                  <li
                    style={{ pointerEvents: 'none', padding: 0 }}
                    key={option.id}
                  >
                    <Button
                      sx={{
                        pointerEvents: 'auto',
                        height: '100%',
                        width: '100%',
                        display: 'flex',
                        justifyContent: 'start',
                        fontWeight: 400,
                        color: 'black',
                        textTransform: 'none'
                      }}
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
                  label="Search Organizations"
                  onBlur={() => setIsOpen(false)}
                />
              )}
            />
          ) : (
            <></>
          )}
          <List sx={{ width: '100%' }}>
            {organizationsInFilters?.map((org) => {
              return (
                <ListItem key={org.id} sx={{ padding: '0px' }}>
                  <FormGroup>
                    <FormControlLabel
                      sx={{ padding: '0px' }}
                      disabled={userLevel === STANDARD_USER}
                      label={org?.name}
                      control={<Checkbox />}
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
          <br />
        </AccordionDetails>
      </Accordion>
    </>
  );
};

interface RegionItemProps {
  regionId: string;
  handleChange: (regionId: string) => void;
  checked: boolean;
}

const RegionItem: React.FC<RegionItemProps> = ({
  regionId: region,
  handleChange,
  checked
}) => {
  return (
    <ListItem sx={{ padding: '0px' }} key={`region-filter-item-${region}`}>
      <FormGroup>
        <FormControlLabel
          control={<Checkbox />}
          label={`Region ${region}`}
          checked={checked}
          onChange={() => {
            handleChange(region);
          }}
          sx={{ padding: '0px' }}
        />
      </FormGroup>
    </ListItem>
  );
};
