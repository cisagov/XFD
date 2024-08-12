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
import { OrganizationShallow, useFilterContext } from 'context/FilterContext';

const GLOBAL_ADMIN = 3;
const REGIONAL_ADMIN = 2;
const STANDARD_USER = 1;

// Swap this value to allow regional admin to filter on regions that aren't their own
export const toggleRegionalUserType = true;

export const OrganizationSearch: React.FC = () => {
  const history = useHistory();
  const {
    showAllOrganizations,
    currentOrganization,
    setShowAllOrganizations,
    setShowMaps,
    user,
    apiGet,
    apiPost
  } = useAuthContext();

  //Are we still using this?
  // const [tags, setTags] = useState<OrganizationTag[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [orgResults, setOrgResults] = useState<OrganizationShallow[]>([]);
  const [regionList, setRegionList] = useState<{ regionId: string }[]>([]);

  const {
    regions,
    setRegions,
    organizations,
    setOrganizations,
    addOrganization,
    removeOrganization
  } = useFilterContext();

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
      if (
        userLevel === STANDARD_USER ||
        (userLevel === REGIONAL_ADMIN && toggleRegionalUserType)
      ) {
        if (user?.regionId) {
          setRegionList([{ regionId: user?.regionId }]);
          return;
        }
      }
      if (userLevel === REGIONAL_ADMIN && toggleRegionalUserType) {
      }
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
          body: { hits: { hits: { _source: OrganizationShallow }[] } };
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

  console.log('CORG', currentOrganization);

  return (
    <>
      <Divider />
      <Accordion expanded={userLevel === STANDARD_USER ? true : undefined}>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>Region(s)</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            {regionList
              .sort((a, b) => parseInt(a.regionId) - parseInt(b.regionId))
              .map((region) => {
                return (
                  <ListItem sx={{ padding: '0px' }} key={region.regionId}>
                    <FormGroup>
                      <FormControlLabel
                        control={<Checkbox />}
                        disabled={
                          userLevel === STANDARD_USER || toggleRegionalUserType
                        }
                        label={`Region ${region.regionId}`}
                        checked={
                          regions.includes(region.regionId) ||
                          userLevel === STANDARD_USER ||
                          toggleRegionalUserType
                        }
                        onChange={() => handleCheckboxChange(region.regionId)}
                        sx={{ padding: '0px' }}
                      />
                    </FormGroup>
                  </ListItem>
                );
              })}
          </List>
        </AccordionDetails>
      </Accordion>
      <Accordion
        defaultExpanded
        expanded={userLevel === STANDARD_USER ? true : undefined}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>Organization(s)</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {/* Need to reconcile type issues caused by adding freeSolo prop */}
          {userLevel !== STANDARD_USER ? (
            <Autocomplete
              onInputChange={(_, v) => handleChange(v)}
              // freeSolo
              disableClearable
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
                  addOrganization(value);
                  setSearchTerm('');
                  if (value.name === 'Election') {
                    setShowMaps(true);
                  } else {
                    setShowMaps(false);
                  }
                  //Are we still using this?
                  // Check if we're on an organization page and, if so, update it to the new organization
                  // if (orgPageMatch !== null) {
                  //   if (!tags.find((e) => e.id === value.id)) {
                  //     history.push(`/organizations/${value.id}`);
                  //   }
                  // }
                } else {
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
          ) : (
            <></>
          )}
          {organizations.map((org) => {
            return (
              <List key={org.id} sx={{ width: '100%' }}>
                <ListItem sx={{ padding: '0px' }}>
                  <FormGroup>
                    <FormControlLabel
                      sx={{ padding: '0px' }}
                      disabled={userLevel === STANDARD_USER}
                      label={org?.name}
                      control={<Checkbox />}
                      checked={true}
                      onChange={() => {
                        const newOrgs = organizations.filter(
                          (o) => o.id !== org.id
                        );
                        setOrganizations(newOrgs);
                      }}
                      // onChange={() => {
                      //   setOrganization(null);
                      //   setShowMaps(false);
                      // }}
                    />
                  </FormGroup>
                </ListItem>
              </List>
            );
          })}
          <br />
        </AccordionDetails>
      </Accordion>
    </>
  );
};
