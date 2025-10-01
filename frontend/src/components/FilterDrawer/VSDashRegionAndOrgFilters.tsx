import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Box, Button, TextField } from '@mui/material';
import Autocomplete from '@mui/material/Autocomplete';
import { useAuthContext } from 'context';
import { useStaticsContext } from 'context/StaticsContext';
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
  const [search_term, setSearchTerm] = useState<string>('');
  const [orgResults, setOrgResults] = useState<OrganizationShallow[]>([]);
  const [isRegOpen, setIsRegOpen] = useState(false);
  const [isOrgOpen, setIsOrgOpen] = useState(false);
  // Initialize selectedRegion - let the effect handle setting the correct value
  const [selectedRegion, setSelectedRegion] = useState<string | undefined>(undefined);

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
        console.log('Searching organizations with regions:', regions, 'search_term:', search_term);
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
          console.log('Raw orgs from API:', orgs.map(o => o.name));

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
          console.log('After exclusions filter:', refinedOrgs.map(o => o.name));
          
          // Don't filter out organizations when changing regions - show all available orgs
          // This allows users to see all organizations in the selected region
          const filteredOrgs = refinedOrgs;
          console.log('After already-filtered check:', filteredOrgs.map(o => o.name));
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
          
          console.log('Final org results being set:', sortedOrgs.map(o => o.name));
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
    if (selectedRegion === allRegionsOption) {
      // If "All Regions" is selected, include all regions
      return regions;
    }
    
    // If a region is currently selected in the UI, use that
    if (selectedRegion) {
      return [selectedRegion];
    }
    
    // Otherwise, check if there's a region filter
    const regionFilter = filters.find(
      (filter) => filter.field === REGION_FILTER_KEY
    );
    if (regionFilter && Array.isArray(regionFilter.values) && regionFilter.values.length > 0) {
      return regionFilter.values as string[];
    }
    
    // Final fallback to user's region
    const userRegion = user?.region_id;
    return userRegion ? [userRegion] : [];
  }, [filters, user?.region_id, selectedRegion, regions]);

  useEffect(() => {
    searchOrganizations(search_term, regionFilterValues ?? []);
  }, [searchOrganizations, search_term, regionFilterValues]);

  // Simple sync: use filter values if they exist, otherwise use user's default
  useEffect(() => {
    const regionFilter = filters.find((filter) => filter.field === REGION_FILTER_KEY);
    
    if (regionFilter && regionFilter.values && regionFilter.values.length > 0) {
      // Use the filtered region
      const targetRegion = regionFilter.values[0] as string;
      if (targetRegion !== selectedRegion) {
        setSelectedRegion(targetRegion);
      }
    } else if (!selectedRegion && user?.region_id) {
      // Only set user's default if no region is currently selected
      setSelectedRegion(user.region_id);
    }
  }, [filters, selectedRegion, user?.region_id]);

  // Sync local selectedOrg state with restored filters
  useEffect(() => {
    const orgFilter = filters.find((filter) => filter.field === ORGANIZATION_FILTER_KEY);
    
    if (orgFilter && orgFilter.values && orgFilter.values.length > 0) {
      const firstOrg = orgFilter.values[0];
      // Check if it's an organization object or just an ID
      if (typeof firstOrg === 'object' && firstOrg.id) {
        // It's an organization object
        if (!selectedOrg || selectedOrg.id !== firstOrg.id) {
          setSelectedOrg(firstOrg as OrganizationShallow);
        }
      } else if (typeof firstOrg === 'string') {
        // It's just an ID, try to find the full org data
        // For now, create a minimal org object if we don't have the full data
        if (!selectedOrg || selectedOrg.id !== firstOrg) {
          // We might need to fetch organization details here, 
          // but for now just clear the selection since we don't have full data
          // This could be improved by fetching org details by ID
        }
      }
    } else {
      // No org filter exists - fall back to user's current organization
      const defaultOrg = shallowCurrentOrg(currentOrganization as Organization);
      if (defaultOrg && (!selectedOrg || selectedOrg.id !== defaultOrg.id)) {
        setSelectedOrg(defaultOrg);
        
        // Also add the default organization as a filter so the dashboard shows the right data
        if (defaultOrg) {
          addFilter(ORGANIZATION_FILTER_KEY, defaultOrg, 'any');
        }
      }
    }
  }, [filters, selectedOrg, currentOrganization, addFilter]);

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
