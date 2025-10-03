import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Box, Button, TextField } from '@mui/material';
import Autocomplete from '@mui/material/Autocomplete';
import { useAuthContext } from 'context';
import { useStaticsContext } from 'context/StaticsContext';
import { useNavigationContext } from 'context/NavigationContext';
import {
  useUserLevel,
  GLOBAL_ADMIN,
  GLOBAL_VIEW,
  REGIONAL_ADMIN,
  STANDARD_USER
} from 'hooks/useUserLevel';
import { ORGANIZATION_EXCLUSIONS } from 'hooks/useUserTypeFilters';
import { OrganizationShallow } from './RegionAndOrganizationFilters';
import { Organization } from 'types';

// Swap this value to allow regional admin to filter on regions that aren't their own
export const toggleRegionalUserType = true;

export const REGION_FILTER_KEY = 'organization.region_id';
export const ORGANIZATION_FILTER_KEY = 'organization_id';

interface VSRegionAndOrgFiltersProps {
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
}

export const VSDashRegionAndOrgFilters: React.FC<
  VSRegionAndOrgFiltersProps
> = ({ addFilter, removeFilter, filters }) => {
  const { user, apiPost, currentOrganization } = useAuthContext();
  const { regions } = useStaticsContext();
  const { isDrillDown } = useNavigationContext();
  const [search_term, setSearchTerm] = useState<string>('');
  const [orgResults, setOrgResults] = useState<OrganizationShallow[]>([]);
  const [isRegOpen, setIsRegOpen] = useState(false);
  const [isOrgOpen, setIsOrgOpen] = useState(false);
  // Initialize selectedRegion - let the effect handle setting the correct value
  const [selectedRegion, setSelectedRegion] = useState<string | undefined>(
    undefined
  );

  const userLevel = useUserLevel().userLevel;

  const shallowCurrentOrg = (currentOrganization: Organization | null) => {
    if (!currentOrganization) {
      return undefined;
    }

    return {
      id: currentOrganization.id,
      name: currentOrganization.name,
      root_domains: currentOrganization.root_domains,
      region_id: currentOrganization.region_id ?? '' // fallback to empty string if undefined
    };
  };

  // Initialize selectedOrg - let the effect handle setting the correct value
  const [selectedOrg, setSelectedOrg] = useState<
    OrganizationShallow | undefined
  >(undefined);

  const searchOrganizations = useCallback(
    async (search_term: string, regions?: string[]) => {
      if (userLevel !== STANDARD_USER) {
        try {
          const results = await apiPost<{
            body: { hits: { hits: { _source: OrganizationShallow }[] } };
          }>('/search/organizations', {
            body: {
              search_term,
              regions
            }
          });

          const body = results?.body?.hits?.hits;
          if (!Array.isArray(body)) {
            return [];
          }

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
      }
    },
    [apiPost, setOrgResults, filters]
  );

  const allRegionsOption = 'All Regions';

  const allRegions = useMemo(() => {
    if (userLevel === GLOBAL_ADMIN || userLevel === GLOBAL_VIEW) {
      return [allRegionsOption, ...regions];
    }
    return regions;
  }, [allRegionsOption, regions]);

  const regionFilterValues = useMemo(() => {
    const regionFilter = filters.find(
      (filter) => filter.field === REGION_FILTER_KEY
    );
    const userRegion = user?.region_id;

    if (selectedRegion === allRegionsOption) {
      // If "All Regions" is selected, include all regions
      return regions;
    }
    // Applies user's region id on initial load
    if (
      !regionFilter ||
      !Array.isArray(regionFilter.values) ||
      (regionFilter.values.length === regions.length &&
        regionFilter.values.includes(userRegion))
    ) {
      return userRegion ? [userRegion] : [];
    }
    return regionFilter.values as string[];
  }, [filters, user?.region_id, selectedRegion, regions]);

  useEffect(() => {
    searchOrganizations(search_term, regionFilterValues ?? []);
  }, [searchOrganizations, search_term, regionFilterValues]);

  // Initialize UI state with user defaults - only run once on mount
  useEffect(() => {
    // Don't run initialization during drill-down scenarios
    if (isDrillDown) {
      return;
    }

    // Set user's default region if not already set
    if (!selectedRegion && user?.region_id) {
      console.log('Initializing with user default region:', user.region_id);
      setSelectedRegion(user.region_id);

      // Also add the user's default region as a filter to ensure correct drill-down behavior
      // This prevents other region filters from being stored during drill-down
      const existingRegionFilter = filters.find(
        (filter) => filter.field === REGION_FILTER_KEY
      );
      if (
        !existingRegionFilter ||
        existingRegionFilter.values[0] !== user.region_id
      ) {
        console.log(
          'Adding user default region filter to ensure correct drill-down:',
          user.region_id
        );
        // Remove any existing region filters first
        if (existingRegionFilter && existingRegionFilter.values) {
          existingRegionFilter.values.forEach((value: string) => {
            removeFilter(REGION_FILTER_KEY, value, 'any');
          });
        }
        addFilter(REGION_FILTER_KEY, user.region_id, 'any');
      }
    }

    // Set user's default organization if not already set
    if (!selectedOrg && currentOrganization) {
      const defaultOrg = shallowCurrentOrg(currentOrganization as Organization);
      if (defaultOrg) {
        console.log('Initializing with user default org:', defaultOrg.name);
        setSelectedOrg(defaultOrg);
      }
    }
    // Only run on mount and when user/currentOrganization become available
    // Don't run during drill-down scenarios to avoid interfering with restoration
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.region_id, currentOrganization?.id, isDrillDown]);

  // Handle drill-down filter restoration - only during drill-down scenarios
  useEffect(() => {
    // Only restore filters when returning from drill-down
    if (!isDrillDown) {
      return;
    }

    const regionFilter = filters.find(
      (filter) => filter.field === REGION_FILTER_KEY
    );
    const orgFilter = filters.find(
      (filter) => filter.field === ORGANIZATION_FILTER_KEY
    );

    console.log('Drill-down detected, checking for filter restoration');

    // Restore region filter if it exists and differs from current selection
    if (regionFilter && regionFilter.values && regionFilter.values.length > 0) {
      const targetRegion = regionFilter.values[0] as string;
      if (targetRegion !== selectedRegion) {
        console.log('Restoring region filter from drill-down:', targetRegion);
        setSelectedRegion(targetRegion);
      }
    }

    // Restore organization filter if it exists and differs from current selection
    if (orgFilter && orgFilter.values && orgFilter.values.length > 0) {
      const firstOrg = orgFilter.values[0];
      if (typeof firstOrg === 'object' && firstOrg.id) {
        if (!selectedOrg || selectedOrg.id !== firstOrg.id) {
          console.log('Restoring org filter from drill-down:', firstOrg.name);
          setSelectedOrg(firstOrg as OrganizationShallow);
        }
      }
    } else {
      // If no explicit org filter exists, restore the default organization
      // This handles the case where user was using default org before drill-down
      if (!selectedOrg && currentOrganization) {
        const defaultOrg = shallowCurrentOrg(currentOrganization as Organization);
        if (defaultOrg) {
          console.log('Restoring default org after drill-down:', defaultOrg.name);
          setSelectedOrg(defaultOrg);
        }
      }
    }
  }, [isDrillDown, filters, selectedRegion, selectedOrg, currentOrganization]);

  const handleTextChange = (v: string) => {
    setSearchTerm(v);
  };

  const handleChangeRegion = (region_id: string) => {
    if (region_id) {
      const existingRegions =
        filters.find((filter) => filter.field === REGION_FILTER_KEY)?.values ||
        [];
      const existingOrgs =
        filters.find((filter) => filter.field === ORGANIZATION_FILTER_KEY)
          ?.values || [];
      existingRegions.forEach((existingRegion: string) => {
        removeFilter(REGION_FILTER_KEY, existingRegion, 'any');
      });
      existingOrgs.forEach((existingOrg: OrganizationShallow) => {
        removeFilter(ORGANIZATION_FILTER_KEY, existingOrg, 'any');
      });
      if (region_id === allRegionsOption) {
        regions.forEach((region) => {
          addFilter(REGION_FILTER_KEY, region, 'any');
        });
      } else {
        addFilter(REGION_FILTER_KEY, region_id, 'any');
      }

      setSelectedRegion(region_id);
      setSelectedOrg(undefined);
      setSearchTerm('');
      setIsRegOpen(false);
    }
  };

  const handleChangeOrganization = (org: OrganizationShallow) => {
    if (!org) return;

    const existingOrgs =
      filters.find((filter) => filter.field === ORGANIZATION_FILTER_KEY)
        ?.values || [];
    existingOrgs.forEach((existingOrg: OrganizationShallow) => {
      removeFilter(ORGANIZATION_FILTER_KEY, existingOrg, 'any');
    });
    addFilter(ORGANIZATION_FILTER_KEY, org, 'any');
    setSelectedOrg(org);
    setSearchTerm('');
    setIsOrgOpen(false);
  };

  return (
    <>
      <Box padding={2}>
        <Autocomplete
          value={selectedRegion ?? ''}
          onChange={(e, v) => {
            setTimeout(() => {
              handleChangeRegion(v);
            }, 250);
            return;
          }}
          onInputChange={(e, v) => {
            if (e && e.type === 'change') {
              handleTextChange(v);
            }
          }}
          disableClearable
          disabled={
            !userLevel ||
            userLevel === REGIONAL_ADMIN ||
            userLevel === STANDARD_USER
          }
          open={isRegOpen}
          onOpen={() => {
            setIsRegOpen(true);
          }}
          options={allRegions}
          getOptionLabel={(option) =>
            allRegionsOption === option ? allRegionsOption : `Region ${option}`
          }
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
                      handleChangeRegion(option);
                    }, 250)
                  }
                >
                  {option === allRegionsOption
                    ? allRegionsOption
                    : `Region ${option}`}
                </Button>
              </li>
            );
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Region"
              placeholder={
                userLevel === GLOBAL_ADMIN || userLevel === GLOBAL_VIEW
                  ? 'Select Region'
                  : ''
              }
              onBlur={() => setIsRegOpen(false)}
            />
          )}
        />
        {/* Need to reconcile type issues caused by adding freeSolo prop */}
      </Box>
      <Box padding={2}>
        <Autocomplete
          key={selectedRegion ? selectedRegion : 'no-region'}
          value={selectedOrg}
          onChange={(e, v) => {
            setTimeout(() => {
              handleChangeOrganization(v);
            }, 250);
            return;
          }}
          onInputChange={(e, v) => {
            if (e && e.type === 'change') {
              handleTextChange(v);
            }
          }}
          // freeSolo
          disableClearable
          disabled={userLevel === STANDARD_USER}
          open={isOrgOpen}
          onOpen={() => {
            setIsOrgOpen(true);
          }}
          options={orgResults}
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
                style={{
                  pointerEvents: 'none',
                  padding: 0
                }}
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
                      handleChangeOrganization(option);
                    }, 250)
                  }
                >
                  {option.name}
                </Button>
              </li>
            );
          }}
          isOptionEqualToValue={(option, value) => option?.name === value?.name}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Organization"
              placeholder="Search Organizations"
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
      </Box>
    </>
  );
};
