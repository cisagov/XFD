import React, { useCallback, useEffect, useState } from 'react';
import { TextField, useTheme } from '@mui/material';
import { Autocomplete } from '@mui/material';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import { styled } from '@mui/material/styles';
import { useAuthContext } from '@/context';
import {
  REGIONAL_ADMIN,
  GLOBAL_ADMIN,
  STANDARD_USER,
  useUserLevel
} from 'hooks/useUserLevel';
import { GLOBAL_VIEW } from '@/context/userStateUtils';

// interface Props {
//   value: string;
//   onChange(value: string): void;
//   placeholder?: string;
// }

export const DomainAndIPFilter: React.FC<{}> = (
  {
    //   value,
    //   onChange,
    //   placeholder
  }
) => {
  const { user, apiPost } = useAuthContext();
  const theme = useTheme();
  const [search_term, setSearchTerm] = useState<string>('');
  const [domainResults, setDomainResults] = useState<
    { id: string; name: string }[]
  >([]);
  const [selectedDomain, setSelectedDomain] = useState<
    | {
        id: string;
        name: string;
      }
    | undefined
  >(undefined);
  const [isDomainOpen, setIsDomainOpen] = React.useState(false);

  const userLevel = useUserLevel().userLevel;

  const searchDomainsAndIPs = useCallback(
    async (search_term: string) => {
      try {
        const response = await apiPost<{
          body: { results: { id: string; name: string }[] };
        }>('/search/domains', {
          body: { search_term }
        });
        console.log('Domain and IP search response:', response);
        setDomainResults(response.body.results);
      } catch (error) {
        console.error('Error fetching domain and IP search results:', error);
        return [];
      }
    },
    [apiPost]
  );

  const handleChangeDomain = (
    newValue: { id: string; name: string } | null
  ) => {
    if (newValue) {
      setSelectedDomain(newValue);
    }
  };

  const handleTextChange = (text: string) => {
    setSearchTerm(text);
  };

  useEffect(() => {
    if (search_term && search_term.length >= 2) {
      searchDomainsAndIPs(search_term);
    } else {
      setDomainResults([]);
    }
  }, [search_term, searchDomainsAndIPs]);

  return (
    <Box padding={2}>
      <Autocomplete
        //   key={selectedDomain ? selectedDomain : 'no-domain'}
        value={selectedDomain}
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
        //   disabled={userLevel === STANDARD_USER}
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
        isOptionEqualToValue={(option, value) => option?.name === value?.name}
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
