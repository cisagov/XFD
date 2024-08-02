import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouteMatch, useHistory } from 'react-router-dom';
import { useAuthContext } from 'context';
import { Organization, OrganizationTag } from 'types';
import {
  Autocomplete,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  TextField
} from '@mui/material';
import { CheckBox } from '@mui/icons-material';

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
    apiGet
  } = useAuthContext();

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [tags, setTags] = useState<OrganizationTag[]>([]);

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
  }, [fetchOrganizations, userLevel]);

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

  const topTenOrganizations = useMemo(() => {
    return organizations.slice(0, 10);
  }, [organizations]);

  console.log('top 10', topTenOrganizations);
  return (
    <>
      {organizations.length > 1 && (
        <Autocomplete
          isOptionEqualToValue={(option, value) => option?.name === value?.name}
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
                  option?.name.toLowerCase() === state.inputValue.toLowerCase()
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
          renderOption={(props, option) => <li {...props}>{option!.name}</li>}
          onChange={(
            event: any,
            value: Organization | { name: string } | undefined
          ) => {
            if (value && 'id' in value) {
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
      {topTenOrganizations.map((org) => (
        <List sx={{ width: '100%' }} key={org.id}>
          <ListItem sx={{ padding: '0px' }}>
            <ListItemButton sx={{ padding: '0px' }}>
              <ListItemIcon>
                <CheckBox />
              </ListItemIcon>
              <ListItemText primary={org.name} />
            </ListItemButton>
          </ListItem>
        </List>
      ))}
    </>
  );
};
