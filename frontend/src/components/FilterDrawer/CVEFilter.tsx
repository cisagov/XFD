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

export const CVE_FILTER_KEY = 'vulnerabilities.cve';

export interface CVEResult {
  id: string;
  name?: string;
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

export const CVEFilter: React.FC<Props> = ({
  addFilter,
  removeFilter,
  filters
}) => {
  const { apiPost } = useAuthContext();
  const [cveResults, setCveResults] = useState<CVEResult[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedCVE, setSelectedCVE] = useState<CVEResult | undefined>(
    undefined
  );

  const theme = useTheme();

  const searchCVEs = useCallback(
    async (search_term: string) => {
      try {
        const results = await apiPost<{
          body: {
            hits: {
              hits: { _source: CVEResult }[];
            };
          };
        }>(ENDPOINTS.CVE_SEARCH_ES, {
          body: { search_term }
        });
        const body = results?.body?.hits?.hits;
        if (body) {
          const rawCVEResults = body
            .filter((hit) => !!hit._source.name)
            .map((hit) => hit._source);

          const filteredCveResults = rawCVEResults.filter((hit) => {
            const isFiltered = !!filters.find(
              (filter) =>
                filter.field === CVE_FILTER_KEY &&
                filter.values.includes(hit.name)
            );
            return !isFiltered;
          });

          const sortedCveResults = filteredCveResults.sort((a, b) => {
            const aName = a.name ?? '';
            const bName = b.name ?? '';
            return aName.localeCompare(bName);
          });

          setCveResults(sortedCveResults);
        } else {
          setCveResults([]);
        }
      } catch (error) {
        logger.error('Error fetching CVE search results:', error);
        setCveResults([]);
      }
    },
    [apiPost, filters]
  );

  const cvesInFilters = useMemo(() => {
    return filters
      .filter((f) => f.field === CVE_FILTER_KEY)
      .flatMap((f) => f.values);
  }, [filters]);

  const handleUseCVEResult = (result: CVEResult | undefined) => {
    if (result && result.name) {
      addFilter(CVE_FILTER_KEY, result.name, 'any');
      setSearchTerm('');
      setSelectedCVE(undefined);
    }
  };
  const handleTextChange = (text: string) => {
    setSearchTerm(text);
  };

  useEffect(() => {
    searchCVEs(searchTerm);
  }, [searchCVEs, searchTerm, filters]);

  return (
    <Box>
      <Autocomplete
        key={selectedCVE ? selectedCVE.id : 'none'}
        value={selectedCVE}
        inputValue={searchTerm}
        onChange={(e, v) => {
          setTimeout(() => {
            setSelectedCVE(v as CVEResult | undefined);
            handleUseCVEResult(v as CVEResult | undefined);
          }, 250);
          return;
        }}
        onInputChange={(e, v, reason) => {
          // Only update the input value when the user types (reason === 'input').
          // This prevents selection/programmatic events from repopulating the input.
          if (reason === 'input') {
            handleTextChange(v);
          }
        }}
        // freeSolo
        disableClearable
        options={cveResults}
        getOptionLabel={(option) => option.name ?? ''}
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
                    setSelectedCVE(option);
                    handleUseCVEResult(option);
                  }, 250)
                }
              >
                {option.name}
              </Button>
            </li>
          );
        }}
        isOptionEqualToValue={(option, value) => {
          if (option.id !== value.id) return false;
          return true;
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label={'Search CVEs'}
            placeholder="Search"
            helperText={
              'This search shows up to 10 CVEs to start. Begin typing to search across all of your available CVEs and select one.'
            }
          />
        )}
      />

      <List sx={{ width: '100%', maxHeight: 5 * 42, overflowY: 'auto' }}>
        {cvesInFilters?.map((cveName: string, id: number) => {
          return (
            <ListItem key={id} sx={{ padding: '0px' }}>
              <FormGroup>
                <FormControlLabel
                  sx={{ padding: '0px' }}
                  label={
                    <Typography variant="body1" key={id}>
                      {cveName}
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
                    const exists = cvesInFilters.find(
                      (v: string) => v === cveName
                    );
                    if (exists) {
                      removeFilter(CVE_FILTER_KEY, cveName, 'any');
                    } else {
                      addFilter(CVE_FILTER_KEY, cveName, 'any');
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
