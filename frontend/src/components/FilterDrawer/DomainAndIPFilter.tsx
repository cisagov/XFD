import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormGroup from '@mui/material/FormGroup';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';
import { useAuthContext } from '@/context';
import { logger } from '@/utils/logger';
import { ENDPOINTS } from '@/constants/endpoints';

export const DOMAIN_FILTER_KEY = 'name';
export const ORGANIZATION_FILTER_KEY = 'organization_id';
export const REGION_FILTER_KEY = 'organization.region_id';

export interface ResultShallow {
  id: string;
  name?: string;
  ip?: string;
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
  const { apiPost } = useAuthContext();
  const [domainResults, setDomainResults] = useState<ResultShallow[]>([]);
  const [domainSearchTerm, setDomainSearchTerm] = useState<string>('');
  const [ipResults, setIpResults] = useState<ResultShallow[]>([]);
  const [ipSearchTerm, setIpSearchTerm] = useState<string>('');
  const search_term = search_field === 'name' ? domainSearchTerm : ipSearchTerm;
  const [selectedDomain, setSelectedDomain] = useState<ResultShallow | null>(
    null
  );
  const [selectedIp, setSelectedIp] = useState<ResultShallow | null>(null);

  const theme = useTheme();

  const compareIp = (a: string, b: string) => {
    const aParts = a.split('.').map(Number);
    const bParts = b.split('.').map(Number);
    for (let i = 0; i < 4; i++) {
      if (aParts[i] !== bParts[i]) {
        return aParts[i] - bParts[i];
      }
    }
    return 0;
  };

  const isIp = (str: string) => {
    return /^\d{1,3}(\.\d{1,3}){3}$/.test(str);
  };

  const searchDomainsAndIPs = useCallback(
    async (
      search_term: string,
      search_field: string,
      regions: string[],
      organizations: string[]
    ) => {
      try {
        const results = await apiPost<{
          body: {
            hits: {
              hits: { _source: ResultShallow }[];
            };
          };
        }>(ENDPOINTS.DOMAIN_IP_SEARCH_ES, {
          body: { search_term, search_field, regions, organizations }
        });
        const body = results?.body?.hits?.hits;
        if (search_field === 'name') {
          const domains = body.filter((hit) => !!hit._source.name);
          const filteredDomains = domains.filter((hit) => {
            const isFiltered = !!filters.find(
              (filter) =>
                filter.field === DOMAIN_FILTER_KEY &&
                filter.values.includes(hit._source.name)
            );
            return !isFiltered;
          });
          const sortedDomains = filteredDomains.sort((a, b) => {
            const aName = a._source.name ?? '';
            const bName = b._source.name ?? '';
            if (isIp(aName) && isIp(bName)) {
              return compareIp(aName, bName);
            }
            return aName.localeCompare(bName);
          });
          setDomainResults(
            sortedDomains.map((hit) => ({
              id: hit._source.id,
              name: hit._source.name
            }))
          );
        } else if (search_field === 'ip') {
          const ips = body.filter((hit) => !!hit._source.ip);
          const filteredIps = ips.filter((hit) => {
            const isFiltered = !!filters.find(
              (filter) =>
                filter.field === 'ip' && filter.values.includes(hit._source.ip)
            );
            return !isFiltered;
          });

          const sortedIps = filteredIps.sort((a, b) =>
            compareIp(a._source.ip ?? '', b._source.ip ?? '')
          );
          setIpResults(
            sortedIps.map((hit) => ({
              id: hit._source.id,
              ip: hit._source.ip
            }))
          );
        } else {
          setDomainResults([]);
          setIpResults([]);
          return [];
        }
      } catch (error) {
        logger.error('Error fetching domain and IP search results:', error);
        setDomainResults([]);
        setIpResults([]);
      }
    },
    [apiPost, filters]
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

  const handleUseDomainResult = (result: ResultShallow | null) => {
    if (result && result.name) {
      addFilter('name', result.name, 'any');
      setDomainSearchTerm('');
      setSelectedDomain(null);
    }
  };

  const handleUseIpResult = (result: ResultShallow | null) => {
    if (result && result.ip) {
      addFilter('ip', result.ip, 'any');
      setIpSearchTerm('');
      setSelectedIp(null);
    }
  };

  const handleDomainTextChange = (text: string) => {
    setDomainSearchTerm(text);
  };

  const handleIpTextChange = (text: string) => {
    setIpSearchTerm(text);
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
        key={
          search_field === 'name'
            ? selectedDomain
              ? selectedDomain.id
              : 'none'
            : selectedIp
              ? selectedIp.id
              : 'none'
        }
        value={
          search_field === 'name'
            ? (selectedDomain ?? undefined)
            : (selectedIp ?? undefined)
        }
        inputValue={search_field === 'name' ? domainSearchTerm : ipSearchTerm}
        onChange={(e, v) => {
          setTimeout(() => {
            if (search_field === 'name') {
              setSelectedDomain(v as ResultShallow | null);
              handleUseDomainResult(v as ResultShallow | null);
            } else {
              setSelectedIp(v as ResultShallow | null);
              handleUseIpResult(v as ResultShallow | null);
            }
          }, 250);
          return;
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            if (search_field === 'name') {
              setSelectedDomain(selectedDomain);
              handleUseDomainResult(selectedDomain);
            } else {
              setSelectedIp(selectedIp);
              handleUseIpResult(selectedIp);
            }
          }
        }}
        onInputChange={(e, v, reason) => {
          // Only update the input value when the user types (reason === 'input').
          // This prevents selection/programmatic events from repopulating the input.
          if (reason === 'input') {
            if (search_field === 'name') {
              handleDomainTextChange(v);
            } else {
              handleIpTextChange(v);
            }
          }
        }}
        // freeSolo
        disableClearable
        options={search_field === 'name' ? domainResults : ipResults}
        getOptionLabel={(option) => option.name ?? option.ip ?? ''}
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
                id="search-results-button"
                onClick={() =>
                  setTimeout(() => {
                    if (search_field === 'name' && option.name) {
                      setSelectedDomain(option);
                      handleUseDomainResult(option);
                    } else if (search_field === 'ip' && option.ip) {
                      setSelectedIp(option);
                      handleUseIpResult(option);
                    }
                  }, 250)
                }
              >
                {'name' in option ? option.name : option.ip}
              </Button>
            </li>
          );
        }}
        isOptionEqualToValue={(option, value) => {
          if (option.id !== value.id) return false;
          if (search_field === 'name') {
            return option.name === value.name;
          } else {
            return option.ip === value.ip;
          }
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label={
              search_field === 'ip' ? 'Search IP Address' : 'Search Domains'
            }
            placeholder="Search"
            helperText={
              search_field === 'name'
                ? 'This search shows up to 10 domains to start. Begin typing to search across all of your available domains and select one.'
                : 'This search shows up to 10 IP addresses to start. Begin typing to search across all of your available IPs and select one.'
            }
          />
        )}
      />

      <List sx={{ width: '100%', maxHeight: 5 * 42, overflowY: 'auto' }}>
        {search_field === 'name' &&
          domainsInFilters?.map((resultName: string, id: string) => {
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
                        (v: string) => v === resultName
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
