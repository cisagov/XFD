import React, { useCallback, useEffect, useState } from 'react';
import { useRouteMatch, useHistory } from 'react-router-dom';
import { useAuthContext } from 'context';
import { Organization } from 'types';
//Are we still using this?
// import  {OrganizationTag} from 'types';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Autocomplete,
  Checkbox,
  Divider,
  FormControlLabel,
  FormGroup,
  List,
  ListItem,
  TextField,
  Toolbar,
  Typography
} from '@mui/material';
import { ExpandMore } from '@mui/icons-material';
import { debounce } from 'utils/debounce';
import { useFiltercontext } from 'context/FilterContext';

const GLOBAL_ADMIN = 3;
const REGIONAL_ADMIN = 2;
const STANDARD_USER = 1;

export const OrganizationSearch: React.FC = () => {
  const history = useHistory();
  const {
    currentOrganization,
    setOrganization,
    showAllOrganizations,
    setShowAllOrganizations,
    setShowMaps,
    user,
    apiGet,
    apiPost
  } = useAuthContext();

  //Are we still using this?
  // const [tags, setTags] = useState<OrganizationTag[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [orgResults, setOrgResults] = useState<Organization[]>([]);
  const [regionList, setRegionList] = useState<{ regionId: string }[]>([]);

  const { regions, setRegions } = useFiltercontext();

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

  const fetchRegions = useCallback(async () => {
    try {
      const results = await apiGet('/regions');
      setRegionList(results);
      setRegions(
        results.map((region: { regionId: any }) => region.regionId).sort()
      );
    } catch (e) {
      console.log(e);
    }
  }, [apiGet, setRegionList, setRegions]);

  const searchOrganizations = useCallback(
    async (searchTerm: string, regions?: string[]) => {
      try {
        const results = await apiPost<{
          body: { hits: { hits: { _source: Organization }[] } };
        }>('/search/organizations', {
          body: {
            searchTerm,
            regions
          }
        });
        const orgs = results.body.hits.hits.map((hit) => hit._source);
        setOrgResults(orgs);
      } catch (e) {
        console.log(e);
      }
    },
    [apiPost, setOrgResults]
  );

  const handleCheckboxChange = (regionId: string) => {
    const selection = () => {
      if (regions.includes(regionId)) {
        return regions.filter((r) => r !== regionId);
      }
      return [...regions, regionId];
    };
    setRegions(selection());
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newSearchTerm = e.target.value;
    setSearchTerm(newSearchTerm);
  };
  console.log('searchTerm', searchTerm);
  console.log('orgResults', orgResults);
  console.log('regions context', regions);

  const handleChange = (v: string) => {
    debounce(searchOrganizations(v) as any, 400);
  };
  useEffect(() => {
    fetchRegions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    searchOrganizations(searchTerm, regions);
  }, [searchOrganizations, searchTerm, regions]);

  const orgPageMatch = useRouteMatch('/organizations/:id');

  return (
    <>
      {userLevel === GLOBAL_ADMIN && (
        <Toolbar sx={{ justifyContent: 'center' }}>
          <Typography variant="h6">Region(s) & Organization(s)</Typography>
        </Toolbar>
      )}
      {userLevel === REGIONAL_ADMIN ||
        (userLevel === STANDARD_USER && (
          <Toolbar sx={{ justifyContent: 'center' }}>
            <Typography variant="h6">Organization(s)</Typography>
          </Toolbar>
        ))}
      <Divider />
      {userLevel === GLOBAL_ADMIN && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Region(s)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {regionList
                .sort((a, b) => parseInt(a.regionId) - parseInt(b.regionId))
                .map((region) => (
                  <ListItem sx={{ padding: '0px' }} key={region.regionId}>
                    <FormGroup>
                      <FormControlLabel
                        control={<Checkbox />}
                        label={`Region ${region.regionId}`}
                        checked={regions.includes(region.regionId)}
                        onChange={() => handleCheckboxChange(region.regionId)}
                        sx={{ padding: '0px' }}
                      />
                    </FormGroup>
                  </ListItem>
                ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}
      {userLevel === GLOBAL_ADMIN || userLevel === REGIONAL_ADMIN ? (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Organization(s)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {/* Need to reconcile type issues caused by adding freeSolo prop */}
            <Autocomplete
              onInputChange={(_, v) => handleChange(v)}
              freeSolo
              options={orgResults}
              getOptionLabel={(option) => option.name}
              renderOption={(params, option) => {
                return (
                  <li {...params} key={option.id}>
                    {option.name}
                  </li>
                );
              }}
              isOptionEqualToValue={(option, value) =>
                option?.name === value?.name
              }
              onChange={(event, value) => {
                if (value) {
                  setOrganization(value);
                  setShowAllOrganizations(false);
                  if (value.name === 'Election') {
                    setShowMaps(true);
                  } else {
                    setShowMaps(false);
                  }
                  //Are we still using this?
                  // Check if we're on an organization page and, if so, update it to the new organization
                  if (orgPageMatch !== null) {
                    if (!tags.find((e) => e.id === value.id)) {
                      history.push(`/organizations/${value.id}`);
                    }
                  }
                } else {
                  setShowAllOrganizations(true);
                  setShowMaps(false);
                }
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Search Organizations"
                  value={searchTerm}
                  onChange={handleTextChange}
                />
              )}
            />
            {currentOrganization ? (
              <List sx={{ width: '100%' }}>
                <ListItem sx={{ padding: '0px' }}>
                  <FormGroup>
                    <FormControlLabel
                      sx={{ padding: '0px' }}
                      label={currentOrganization?.name}
                      control={<Checkbox />}
                      checked={!showAllOrganizations}
                      onChange={() => {
                        setShowAllOrganizations(true);
                        setOrganization(null);
                        setShowMaps(false);
                      }}
                    />
                  </FormGroup>
                </ListItem>
              </List>
            ) : (
              <></>
            )}
            <br />
          </AccordionDetails>
        </Accordion>
      ) : null}
    </>
  );
};