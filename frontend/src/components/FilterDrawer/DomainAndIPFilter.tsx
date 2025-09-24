import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { TextField, useTheme } from '@mui/material';
import { Autocomplete } from '@mui/material';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import { useAuthContext } from '@/context';
import {
  REGIONAL_ADMIN,
  GLOBAL_ADMIN,
  STANDARD_USER,
  useUserLevel
} from 'hooks/useUserLevel';
import { GLOBAL_VIEW } from '@/context/userStateUtils';
import { useStaticsContext } from '@/context/StaticsContext';

interface Props {
  addFilter: (
    name: string,
    value: string,
    filterType: 'all' | 'any' | 'none'
  ) => void;
  removeFilter: (
    name: string,
    value: string,
    filterType: 'all' | 'any' | 'none'
  ) => void;
  filters: any[];
}

export const DomainAndIPFilter: React.FC<Props> = ({
  addFilter,
  removeFilter,
  filters
}) => {
  const { user, apiPost } = useAuthContext();
  const { regions } = useStaticsContext();
  const [search_term, setSearchTerm] = useState<string>('');
  const [domainResults, setDomainResults] = useState<
    { id: string; name: string }[]
  >([]);
  const [selectedDomain, setSelectedDomain] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [isDomainOpen, setIsDomainOpen] = React.useState(false);

  const userLevel = useUserLevel().userLevel;

  const searchDomainsAndIPs = useCallback(
    async (search_term: string, regions: string[], organizations: string[]) => {
      try {
        const results = await apiPost<{
          body: { hits: { hits: { _source: { id: string; name: string } }[] } };
        }>('/search/domains', {
          body: { search_term, regions, organizations }
        });
        const body = results?.body?.hits?.hits;
        setDomainResults(body.map((hit) => hit._source));
      } catch (error) {
        console.error('Error fetching domain and IP search results:', error);
        setDomainResults([]);
        return [];
      }
    },
    [apiPost]
  );

  const regionFilterValues = useMemo(() => {
    const regionFilter = filters.find(
      (f) => f.field === 'organization.region_id'
    );
    return regionFilter ? (regionFilter.values as string[]) : [];
  }, [filters]);

  const orgFilterValues = useMemo(() => {
    const orgFilters = filters.find((f) => f.field === 'organization_id');
    if (!orgFilters) return [];

    const orgFiltersId = orgFilters.values?.map((val: any) => val.id);
    console.log('orgFiltersId:', orgFiltersId);
    // return orgFilters ? (orgFilters.values.id as string[]) : [];
    return orgFilters ? (orgFiltersId as string[]) : [];
  }, [filters]);

  console.log('regionFilterValues:', regionFilterValues);
  console.log('orgFilterValues:', orgFilterValues);

  const handleChangeDomain = (domain: { id: string; name: string } | null) => {
    if (domain) {
      const existingDomains = filters.find((filter) => filter.field === 'name');
      if (existingDomains) {
        existingDomains.values.forEach((value: string) => {
          removeFilter('name', value, 'any');
        });
      }
      setSelectedDomain(domain);
      addFilter('name', domain.name, 'any');
    }
  };

  console.log('domainResults:', domainResults);
  console.log('selectedDomain:', selectedDomain);
  console.log('filters in DomainAndIPFilter:', filters);

  const handleTextChange = (text: string) => {
    setSearchTerm(text);
  };

  useEffect(() => {
    searchDomainsAndIPs(search_term, regionFilterValues, orgFilterValues);
  }, [search_term, searchDomainsAndIPs, regionFilterValues, orgFilterValues]);

  return (
    <Box>
      <Autocomplete
        // key={selectedDomain ? selectedDomain : 'no-domain'}
        value={selectedDomain ? selectedDomain : undefined}
        onChange={(e, v) => {
          setTimeout(() => {
            handleChangeDomain(v);
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
        open={isDomainOpen}
        onOpen={() => {
          setIsDomainOpen(true);
        }}
        options={domainResults}
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
                    handleChangeDomain(option);
                  }, 250)
                }
              >
                {option.name}
              </Button>
            </li>
          );
        }}
        // isOptionEqualToValue={(option, value) => option?.name === value?.name}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Domain"
            placeholder="Search Domains"
            onBlur={() => setIsDomainOpen(false)}
            helperText={
              userLevel === REGIONAL_ADMIN ||
              userLevel === GLOBAL_ADMIN ||
              userLevel === GLOBAL_VIEW
                ? 'This search shows up to 10 domains to start. Begin typing to search across all domains and select one.'
                : ''
            }
          />
        )}
      />
    </Box>
  );
};
