import React, { useEffect, useState, useCallback } from 'react';
import { logger } from '@/utils/logger';
import { useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Grid from '@mui/material/Grid';
import Link from '@mui/material/Link';
import Paper from '@mui/material/Paper';
import Tab from '@mui/material/Tab';
import Typography from '@mui/material/Typography';
import TabContext from '@mui/lab/TabContext';
import TabList from '@mui/lab/TabList';
import TabPanel from '@mui/lab/TabPanel';
import ChevronRight from '@mui/icons-material/ChevronRight';
import { useAuthContext } from 'context';
import {
  Organization as OrganizationType,
  Role,
  ScanTask,
  OrganizationTag
} from 'types';
import OrgMembers from './OrgMembers';
import OrgSettings from './OrgSettings';
import { ENDPOINTS } from '@/constants/endpoints';
import { ROUTES } from '@/constants/routes';

interface AutocompleteType extends Partial<OrganizationTag> {
  title?: string;
}
export const Organization: React.FC = () => {
  const { apiGet } = useAuthContext();
  const { organizationId } = useParams<{ organizationId: string }>();
  const [organization, setOrganization] = useState<OrganizationType>();
  const [tags, setTags] = useState<AutocompleteType[]>([]);
  const [userRoles, setUserRoles] = useState<Role[]>([]);
  const [, setScanTasks] = useState<ScanTask[]>([]);
  const [tabValue, setTabValue] = React.useState('1');
  const handleTabChange = (event: React.SyntheticEvent, new_value: string) => {
    setTabValue(new_value);
  };

  const fetchOrganization = useCallback(async () => {
    try {
      const organization = await apiGet<OrganizationType>(
        ENDPOINTS.ORGANIZATION.replace('{organization_id}', organizationId)
      );
      organization.scan_tasks.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setOrganization(organization);
      setUserRoles(organization.user_roles);
      setScanTasks(organization.scan_tasks);
      const tags = await apiGet<OrganizationTag[]>(
        ENDPOINTS.ORGANIZATIONS_TAGS
      );
      setTags(tags);
    } catch (e) {
      logger.error('Organization.fetchOrganization failed:', {
        error: e,
        organizationId
      });
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
    <React.Fragment key={2}></React.Fragment>
  ];

  return (
    <Grid container p={2}>
      <Grid size={{ xs: 12 }} mb={2}>
        <Breadcrumbs separator={<ChevronRight />}>
          <Link href="/organizations" variant="h5">
            Organizations
          </Link>
          {organization.parent && (
            <Link
              href={ROUTES.ORGANIZATION.replace(
                ':organizationId',
                organization.parent.id
              )}
            >
              {organization.parent.name}
            </Link>
          )}
          <Typography variant="h5" color="primary">
            {organization.name}
          </Typography>
        </Breadcrumbs>
      </Grid>
      <Grid size={{ xs: 12, md: 2, xl: 3 }} />
      <Grid size={{ xs: 12, md: 8, xl: 6 }}>
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
      <Grid size={{ xs: 12, md: 2, xl: 3 }} />
    </Grid>
  );
};

export default Organization;
