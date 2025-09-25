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
import { useStaticsContext } from '@/context/StaticsContext';

export const DOMAIN_FILTER_KEY = 'name';
export const ORGANIZATION_FILTER_KEY = 'organization_id';
export const REGION_FILTER_KEY = 'organization.region_id';

export interface ResultShallow {
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
  search_field: string;
}

export const DomainAndIPFilter: React.FC<Props> = ({
  addFilter,
  removeFilter,
  filters,
  search_field
}) => {
  const { user, apiPost } = useAuthContext();
  const { regions } = useStaticsContext();
  const [search_term, setSearchTerm] = useState<string>('');
  const [results, setResults] = useState<{ id: string; name: string }[]>([]);
  const [selectedResult, setSelectedResult] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [isDomainOpen, setIsDomainOpen] = React.useState(false);

  const theme = useTheme();
  const userLevel = useUserLevel().userLevel;

  const searchDomainsAndIPs = useCallback(
    async (
      search_term: string,
      search_field: string,
      regions: string[],
      organizations: string[]
    ) => {
      try {
        const results = await apiPost<{
          body: { hits: { hits: { _source: { id: string; name: string } }[] } };
        }>('/search/domains', {
          body: { search_term, search_field, regions, organizations }
        });
        const body = results?.body?.hits?.hits;
        setResults(body.map((hit) => hit._source));
      } catch (error) {
        console.error('Error fetching domain and IP search results:', error);
        setResults([]);
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
    return orgFilters ? (orgFiltersId as string[]) : [];
  }, [filters]);

  const domainsInFilters = useMemo(() => {
    const domainFilters = filters.find(
      (filter) => filter.field === DOMAIN_FILTER_KEY
    );
    return domainFilters ? domainFilters.values : [];
  }, [filters]);

  const ipsInFilters = useMemo(() => {
    const ipFilters = filters.find(
      (filter) => filter.field === 'ip' && filter.values.length > 0
    );
    return ipFilters ? ipFilters.values : [];
  }, [filters]);

  const handleUseResult = (result: { id: string; name: string } | null) => {
    if (result) {
      setSelectedResult(result);
    }
    if (result && search_field === 'name')
      addFilter('name', result.name, 'any');
    if (result && search_field === 'ip') addFilter('ip', result.name, 'any');
  };

  const handleTextChange = (text: string) => {
    setSearchTerm(text);
  };

  useEffect(() => {
    searchDomainsAndIPs(
      search_term,
      search_field,
      regionFilterValues,
      orgFilterValues
    );
  }, [
    search_term,
    search_field,
    searchDomainsAndIPs,
    regionFilterValues,
    orgFilterValues
  ]);

  return (
    <Box>
      <Autocomplete
        key={selectedResult ? selectedResult.id : 'none'}
        value={selectedResult ? selectedResult : undefined}
        onChange={(e, v) => {
          setTimeout(() => {
            handleUseResult(v);
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
        options={results}
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
                    handleUseResult(option);
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
            label={
              search_field === 'ip' ? 'Search IP Address' : 'Search Domains'
            }
            placeholder="Search"
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
        {search_field === 'name' &&
          domainsInFilters?.map((resultName: string, id: string) => {
            console.log('domain in domainsInFilters:', resultName);
            return (
              <ListItem key={id} sx={{ padding: '0px' }}>
                <FormGroup>
                  <FormControlLabel
                    sx={{ padding: '0px' }}
                    label={
                      <Typography variant="body1" key={id}>
                        {resultName}
                      </Typography>
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
                        (result: ResultShallow) => result.id === id
                      );
                      if (exists) {
                        removeFilter(DOMAIN_FILTER_KEY, resultName, 'any');
                      } else {
                        addFilter(DOMAIN_FILTER_KEY, resultName, 'any');
                      }
                    }}
                  />
                </FormGroup>
              </ListItem>
            );
          })}
        {search_field === 'ip' &&
          ipsInFilters?.map((ip: string, index: number) => {
            return (
              <ListItem key={index} sx={{ padding: '0px' }}>
                <FormGroup>
                  <FormControlLabel
                    sx={{ padding: '0px' }}
                    label={
                      <Typography variant="body1" key={index}>
                        {ip}
                      </Typography>
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
                      const exists = ipsInFilters.find((v: string) => v === ip);
                      if (exists) {
                        removeFilter('ip', ip, 'any');
                      } else {
                        addFilter('ip', ip, 'any');
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

// interface DomainCheckboxLabelProps {
//   result: ResultShallow;
// }
// const DomainCheckboxLabel: React.FC<DomainCheckboxLabelProps> = ({
//   result
// }) => {
//   return (
//     <>
//       <Typography variant="body1">{result.name}</Typography>
//     </>
//   );
// };
