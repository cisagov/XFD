import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useAuthContext } from 'context';
import {
  Organization as OrganizationType,
  Role,
  ScanTask,
  OrganizationTag
} from 'types';

import {
  Box,
  Breadcrumbs,
  Grid,
  Link as MuiLink,
  Paper,
  Tab,
  Typography
} from '@mui/material';
import { TabContext, TabList, TabPanel } from '@mui/lab';
import { ChevronRight } from '@mui/icons-material';
import OrgMembers from './OrgMembers';
import OrgScanHistory from './OrgScanHistory';
import OrgSettings from './OrgSettings';

interface AutocompleteType extends Partial<OrganizationTag> {
  title?: string;
}
export const Organization: React.FC = () => {
  const { apiGet } = useAuthContext();
  const { organizationId } = useParams<{ organizationId: string }>();
  const [organization, setOrganization] = useState<OrganizationType>();
  const [tags, setTags] = useState<AutocompleteType[]>([]);
  const [userRoles, setUserRoles] = useState<Role[]>([]);
  const [scanTasks, setScanTasks] = useState<ScanTask[]>([]);
  const [tabValue, setTabValue] = React.useState('1');
  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setTabValue(newValue);
  };

  const fetchOrganization = useCallback(async () => {
    try {
      const organization = await apiGet<OrganizationType>(
        `/organizations/${organizationId}`
      );
      organization.scanTasks.sort(
        (a, b) =>
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      setOrganization(organization);
      setUserRoles(organization.userRoles);
      setScanTasks(organization.scanTasks);
      const tags = await apiGet<OrganizationTag[]>(`/organizations/tags`);
      setTags(tags);
    } catch (e) {
      console.error(e);
    }
  }, [apiGet, setOrganization, organizationId]);

  useEffect(() => {
    fetchOrganization();
  }, [fetchOrganization]);

  if (!organization) return null;

  const views = [
    <Paper key={0}>
      <OrgSettings
        organization={organization}
        setOrganization={setOrganization}
        tags={tags}
      />
    </Paper>,
    <React.Fragment key={1}>
      <OrgMembers
        organization={organization}
        userRoles={userRoles}
        setUserRoles={setUserRoles}
      />
    </React.Fragment>,
    <React.Fragment key={2}>
      <OrgScanHistory
        organization={organization}
        setOrganization={setOrganization}
        scanTasks={scanTasks}
      />
    </React.Fragment>
  ];

  return (
    <Grid container p={2}>
      <Grid item xs={12} mb={2}>
        <Breadcrumbs separator={<ChevronRight />}>
          <MuiLink href="/organizations" variant="h5">
            Organizations
          </MuiLink>
          {organization.parent && (
            <MuiLink href={'/organizations/' + organization.parent.id}>
              {organization.parent.name}
            </MuiLink>
          )}
          <Typography variant="h5" color="primary">
            {organization.name}
          </Typography>
        </Breadcrumbs>
      </Grid>
      <Grid item xs={12} md={2} xl={3} />
      <Grid item xs={12} md={8} xl={6}>
        <TabContext value={tabValue}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <TabList onChange={handleTabChange}>
              <Tab label="Settings" value="1" />
              <Tab label="Members" value="2" />
            </TabList>
          </Box>
          <TabPanel value="1">{views[0]}</TabPanel>
          <TabPanel value="2">{views[1]}</TabPanel>
        </TabContext>
      </Grid>
      <Grid item xs={12} md={2} xl={3} />
    </Grid>
  );
};

export default Organization;
