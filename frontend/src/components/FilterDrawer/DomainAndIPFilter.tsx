import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Autocomplete,
  Box,
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
import { useAuthContext } from '@/context';
import {
  REGIONAL_ADMIN,
  GLOBAL_ADMIN,
  GLOBAL_VIEW,
  STANDARD_USER,
  useUserLevel
} from 'hooks/useUserLevel';
// import { GLOBAL_VIEW } from '@/context/userStateUtils';
import { useStaticsContext } from '@/context/StaticsContext';

export const DOMAIN_FILTER_KEY = 'name';
export const ORGANIZATION_FILTER_KEY = 'organization_id';
export const REGION_FILTER_KEY = 'organization.region_id';

export interface DomainShallow {
  id: string;
  name: string;
}

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

  const theme = useTheme();
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
    const regionFilter = filters.find((f) => f.field === REGION_FILTER_KEY);
    return regionFilter ? (regionFilter.values as string[]) : [];
  }, [filters]);

  const orgFilterValues = useMemo(() => {
    const orgFilters = filters.find((f) => f.field === ORGANIZATION_FILTER_KEY);
    if (!orgFilters) return [];

    const orgFiltersId = orgFilters.values?.map((val: any) => val.id);
    console.log('orgFiltersId:', orgFiltersId);
    // return orgFilters ? (orgFilters.values.id as string[]) : [];
    return orgFilters ? (orgFiltersId as string[]) : [];
  }, [filters]);

  const domainsInFilters = useMemo(() => {
    const domainsFilters = filters.find(
      (filter) => filter.field === DOMAIN_FILTER_KEY
    );
    return domainsFilters ? domainsFilters.values : [];
    // return domainsFilters ? (domainsFilters.values as DomainShallow[]) : [];
  }, [filters]);
  console.log('domainsInFilters:', domainsInFilters);

  console.log('regionFilterValues:', regionFilterValues);
  console.log('orgFilterValues:', orgFilterValues);

  const handleChangeDomain = (domain: { id: string; name: string } | null) => {
    if (domain) {
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

      <List sx={{ width: '100%', maxHeight: 5 * 42, overflowY: 'auto' }}>
        {domainsInFilters?.map((domainName: string, id: string) => {
          console.log('domain in domainsInFilters:', domainName);
          return (
            <ListItem key={id} sx={{ padding: '0px' }}>
              <FormGroup>
                <FormControlLabel
                  sx={{ padding: '0px' }}
                  label={
                    <DomainCheckboxLabel
                      domain={{ name: domainName, id: id }}
                    />
                  }
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
                    const exists = domainsInFilters.find(
                      (domain: DomainShallow) => domain.id === domain.id
                    );
                    if (exists) {
                      removeFilter(DOMAIN_FILTER_KEY, domainName, 'any');
                    } else {
                      addFilter(DOMAIN_FILTER_KEY, domainName, 'any');
                    }
                  }}
                />
              </FormGroup>
            </ListItem>
          );
        })}
      </List>
    </Box>
  );
};

interface DomainCheckboxLabelProps {
  domain: DomainShallow;
}
const DomainCheckboxLabel: React.FC<DomainCheckboxLabelProps> = ({
  domain
}) => {
  return (
    <>
      <Typography variant="body1">{domain.name}</Typography>
    </>
  );
};
