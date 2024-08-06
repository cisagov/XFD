import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouteMatch, useHistory } from 'react-router-dom';
import { useAuthContext } from 'context';
import { Organization, OrganizationTag } from 'types';
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

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [tags, setTags] = useState<OrganizationTag[]>([]);
  const [orgResults, setOrgResults] = useState<Organization[]>([]);
  const [regions, setRegions] = useState<{ regionId: string }[]>([]);

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
      setRegions(results);
    } catch (e) {
      console.log(e);
    }
  }, [apiGet]);

  const searchOrganizations = useCallback(
    async (searchTerm: string) => {
      try {
        const results = await apiPost<{
          body: { hits: { hits: { _source: Organization }[] } };
        }>('/search/organizations', {
          searchTerm
        });
        const orgs = results.body.hits.hits.map((hit) => hit._source);
        setOrgResults(orgs);
      } catch (e) {
        console.log(e);
      }
    },
    [apiPost, setOrgResults]
  );

  const fetchOrganizations = useCallback(async () => {
    try {
      const rows = await apiGet<Organization[]>('/v2/organizations/');
      let tags: OrganizationTag[] = [];
      if (userLevel === GLOBAL_ADMIN) {
        tags = await apiGet<OrganizationTag[]>('/organizations/tags');
        await setTags(tags as OrganizationTag[]);
      }
      await setOrganizations(rows);
    } catch (e) {
      console.log(e);
    }
  }, [apiGet, setOrganizations, userLevel]);

  useEffect(() => {
    if (userLevel > 0) {
      fetchOrganizations();
    }
    searchOrganizations(' ');
    fetchRegions();
  }, [userLevel, fetchOrganizations, searchOrganizations, fetchRegions]);

  const orgPageMatch = useRouteMatch('/organizations/:id');

  const organizationDropdownOptions: Array<{ name: string }> = useMemo(() => {
    if (userLevel === GLOBAL_ADMIN) {
      return [{ name: 'All Organizations' }].concat(organizations);
    }
    if (userLevel === REGIONAL_ADMIN) {
      return organizations.filter((item) => {
        return item.regionId === user?.regionId;
      });
    }
    return [];
  }, [user, organizations, userLevel]);

  const regionIds = useMemo(() => {
    return regions.map((region) => region.regionId).sort();
  }, [regions]);

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
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Region(s)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {regionIds.map((id) => (
                <ListItem sx={{ padding: '0px' }} key={id}>
                  <FormGroup>
                    <FormControlLabel
                      control={<Checkbox />}
                      label={`Region ${id}`}
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
            {organizations.length > 1 && (
              <Autocomplete
                isOptionEqualToValue={(option, value) =>
                  option?.name === value?.name
                }
                options={
                  userLevel === GLOBAL_ADMIN
                    ? [...tags, ...organizationDropdownOptions]
                    : organizationDropdownOptions
                }
                autoComplete={false}
                //   className={classes.selectOrg}
                classes={
                  {
                    // option: classes.option
                  }
                }
                value={
                  showAllOrganizations
                    ? { name: 'All Organizations' }
                    : currentOrganization ?? undefined
                }
                filterOptions={(options, state) => {
                  // If already selected, show all
                  if (
                    options.find(
                      (option) =>
                        option?.name.toLowerCase() ===
                        state.inputValue.toLowerCase()
                    )
                  ) {
                    return options;
                  }
                  return options.filter(
                    (option) =>
                      option?.name
                        .toLowerCase()
                        .includes(state.inputValue.toLowerCase())
                  );
                }}
                disableClearable
                blurOnSelect
                selectOnFocus
                getOptionLabel={(option) => option!.name}
                renderOption={(props, option) => (
                  <li {...props}>{option!.name}</li>
                )}
                onChange={(
                  event: any,
                  value: Organization | { name: string } | undefined
                ) => {
                  if (value && 'id' in value) {
                    console.log('value', value);
                    console.log('value.name', value.name);
                    setOrganization(value);
                    setShowAllOrganizations(false);
                    if (value.name === 'Election') {
                      setShowMaps(true);
                    } else {
                      setShowMaps(false);
                    }
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
                    variant="outlined"
                    inputProps={{
                      ...params.inputProps,
                      id: 'autocomplete-input',
                      autoComplete: 'new-password' // disable autocomplete and autofill
                    }}
                  />
                )}
              />
            )}
            <br />
            <Autocomplete
              options={orgResults}
              getOptionLabel={(option) => option.name}
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
                <TextField {...params} label="Search Organizations" />
              )}
            />
            {!showAllOrganizations && (
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
                        setShowMaps(false);
                      }}
                    />
                  </FormGroup>
                </ListItem>
              </List>
            )}
            <br />
          </AccordionDetails>
        </Accordion>
      ) : null}
    </>
  );
};
