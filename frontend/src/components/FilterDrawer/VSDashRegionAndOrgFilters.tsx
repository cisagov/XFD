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

  const [selectedOrg, setSelectedOrg] = useState<
    OrganizationShallow | undefined
  >(shallowCurrentOrg(currentOrganization as Organization));

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
          value={selectedRegion ?? user?.region_id ?? ''}
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
                userLevel === REGIONAL_ADMIN || userLevel === GLOBAL_ADMIN
                  ? 'This filter, by default, displays data for all organizations in your region. Use this filter to select an organization.'
                  : ''
              }
            />
          )}
        />
      </Box>
    </>
  );
};
