import React, { useEffect, useState, useCallback } from 'react';
import * as OrganizationStyles from './style';
import { Link, useParams } from 'react-router-dom';
import { useAuthContext } from 'context';
import {
  Organization as OrganizationType,
  Role,
  ScanTask,
  OrganizationTag,
  PendingDomain
} from 'types';

import {
  Box,
  Breadcrumbs,
  Chip,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Grid,
  Link as MuiLink,
  Paper,
  Switch as SwitchInput,
  Tab,
  TextField,
  Typography
} from '@mui/material';
import { TabContext, TabList, TabPanel } from '@mui/lab';
import { ChevronRight } from '@mui/icons-material';
import { Autocomplete } from '@mui/material';
import { createFilterOptions } from '@mui/material/useAutocomplete';
import OrgMembers from './OrgMembers';
import OrgScanHistory from './OrgScanHistory';

interface AutocompleteType extends Partial<OrganizationTag> {
  title?: string;
}
export const Organization: React.FC = () => {
  const { apiGet, apiPut, apiPost, user, setFeedbackMessage } =
    useAuthContext();
  const { organizationId } = useParams<{ organizationId: string }>();
  const [organization, setOrganization] = useState<OrganizationType>();
  const [tags, setTags] = useState<AutocompleteType[]>([]);
  const [userRoles, setUserRoles] = useState<Role[]>([]);
  const [scanTasks, setScanTasks] = useState<ScanTask[]>([]);
  const [tabValue, setTabValue] = React.useState('1');
  const [tagValue, setTagValue] = React.useState<AutocompleteType | null>(null);
  const [inputValue, setInputValue] = React.useState('');
  const [dialog, setDialog] = React.useState<{
    open: boolean;
    type?: 'rootDomains' | 'ipBlocks' | 'tags';
    label?: string;
    stage?: number;
    domainVerificationStatusMessage?: string;
  }>({ open: false });
  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setTabValue(newValue);
  };

  const organizationClasses = OrganizationStyles.organizationClasses;

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

  const updateOrganization = async (body: any) => {
    try {
      const org = await apiPut('/organizations/' + organization?.id, {
        body: organization
      });
      setOrganization(org);
      setFeedbackMessage({
        message: 'Organization successfully updated',
        type: 'success'
      });
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422
            ? 'Error updating organization'
            : e.message ?? e.toString(),
        type: 'error'
      });
      console.error(e);
    }
  };

  const initiateDomainVerification = async (domain: string) => {
    try {
      if (!organization) return;
      const pendingDomains: PendingDomain[] = await apiPost(
        `/organizations/${organization?.id}/initiateDomainVerification`,
        {
          body: { domain }
        }
      );
      setOrganization({ ...organization, pendingDomains });
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422
            ? 'Error creating domain'
            : e.message ?? e.toString(),
        type: 'error'
      });
      console.error(e);
    }
  };
  console.log(organization);
  const checkDomainVerification = async (domain: string) => {
    try {
      if (!organization) return;
      const resp: { success: boolean; organization?: OrganizationType } =
        await apiPost(
          `/organizations/${organization?.id}/checkDomainVerification`,
          {
            body: { domain }
          }
        );
      if (resp.success && resp.organization) {
        setOrganization(resp.organization);
        setDialog({ open: false });
        setFeedbackMessage({
          message: 'Domain ' + inputValue + ' successfully verified!',
          type: 'success'
        });
      } else {
        setDialog({
          ...dialog,
          domainVerificationStatusMessage:
            'Record not yet found. Note that DNS records may take up to 72 hours to propagate. You can come back later to check the verification status.'
        });
      }
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422
            ? 'Error verifying domain'
            : e.message ?? e.toString(),
        type: 'error'
      });
      console.error(e);
    }
  };

  useEffect(() => {
    fetchOrganization();
  }, [fetchOrganization]);

  const filter = createFilterOptions<AutocompleteType>();

  const ListInput = (props: {
    type: 'rootDomains' | 'ipBlocks' | 'tags';
    label: string;
  }) => {
    if (!organization) return null;
    const elements: (string | OrganizationTag)[] = organization[props.type];
    return (
      <Grid container spacing={1}>
        <Grid item xs={12} sm={3} lg={2} my={1}>
          <Typography variant="body2">{props.label}</Typography>
        </Grid>
        {elements &&
          elements.map((value: string | OrganizationTag, index: number) => (
            <Grid item mb={1} key={index}>
              <Chip
                color={'primary'}
                className={organizationClasses.chip}
                label={typeof value === 'string' ? value : value.name}
                onDelete={() => {
                  organization[props.type].splice(index, 1);
                  setOrganization({ ...organization });
                }}
              ></Chip>
            </Grid>
          ))}
        {props.type === 'rootDomains' &&
          organization.pendingDomains.map((domain, index: number) => (
            <Grid item mb={1} key={index}>
              <Chip
                className={organizationClasses.chip}
                style={{ backgroundColor: '#C4C4C4' }}
                label={domain.name + ' (verification pending)'}
                onDelete={() => {
                  organization.pendingDomains.splice(index, 1);
                  setOrganization({ ...organization });
                }}
                onClick={() => {
                  setInputValue(domain.name);
                  setDialog({
                    open: true,
                    type: props.type,
                    label: props.label,
                    stage: 1
                  });
                }}
              ></Chip>
            </Grid>
          ))}
        {(props.type === 'rootDomains' || user?.userType === 'globalAdmin') && (
          <Grid item mb={1}>
            <Chip
              label="ADD"
              variant="outlined"
              color="secondary"
              onClick={() => {
                setDialog({
                  open: true,
                  type: props.type,
                  label: props.label,
                  stage: 0
                });
              }}
            />
          </Grid>
        )}
      </Grid>
    );
  };

  if (!organization) return null;

  const views = [
    <Paper key={0}>
      <Dialog
        open={dialog.open}
        onClose={() => setDialog({ open: false })}
        aria-labelledby="form-dialog-title"
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle id="form-dialog-title">
          Add {dialog.label && dialog.label.slice(0, -1)}
        </DialogTitle>
        <DialogContent>
          {dialog.type === 'tags' ? (
            <>
              <DialogContentText>
                Select an existing tag or add a new one.
              </DialogContentText>
              <Autocomplete
                value={tagValue}
                onChange={(event, newValue) => {
                  if (typeof newValue === 'string') {
                    setTagValue({
                      name: newValue
                    });
                  } else {
                    setTagValue(newValue);
                  }
                }}
                filterOptions={(options, params) => {
                  const filtered = filter(options, params);
                  // Suggest the creation of a new value
                  if (
                    params.inputValue !== '' &&
                    !filtered.find(
                      (tag) =>
                        tag.name?.toLowerCase() ===
                        params.inputValue.toLowerCase()
                    )
                  ) {
                    filtered.push({
                      name: params.inputValue,
                      title: `Add "${params.inputValue}"`
                    });
                  }
                  return filtered;
                }}
                selectOnFocus
                clearOnBlur
                handleHomeEndKeys
                options={tags}
                getOptionLabel={(option) => {
                  if (typeof option === 'string') {
                    return option;
                  }
                  return (option as AutocompleteType).name ?? '';
                }}
                renderOption={(props, option) => {
                  if (option.title) return option.title;
                  return option.name ?? '';
                }}
                fullWidth
                freeSolo
                renderInput={(params) => (
                  <TextField {...params} variant="outlined" />
                )}
              />
            </>
          ) : dialog.type === 'rootDomains' && dialog.stage === 1 ? (
            <>
              <DialogContentText>
                Add the following TXT record to {inputValue}&apos;s DNS
                configuration and click Verify.
              </DialogContentText>
              <TextField
                style={{ width: '100%' }}
                value={
                  organization.pendingDomains.find(
                    (domain) => domain.name === inputValue
                  )?.token
                }
                onFocus={(event) => {
                  event.target.select();
                }}
              />
              {dialog.domainVerificationStatusMessage && (
                <>
                  <br></br>
                  <br></br>
                  <DialogContentText>
                    {dialog.domainVerificationStatusMessage}
                  </DialogContentText>
                </>
              )}
            </>
          ) : user?.userType === 'globalAdmin' ? (
            <>
              <DialogContentText>
                Separate multiple entries by commas.
              </DialogContentText>
              <TextField
                autoFocus
                margin="dense"
                id="name"
                inputProps={{ maxLength: 255 }}
                label={dialog.label && dialog.label.slice(0, -1)}
                type="text"
                fullWidth
                onChange={(e) => setInputValue(e.target.value)}
              />
            </>
          ) : dialog.type === 'rootDomains' && dialog.stage === 0 ? (
            <>
              <DialogContentText>
                In order to add a root domain, you will need to verify ownership
                of the domain.
              </DialogContentText>
              <TextField
                autoFocus
                margin="dense"
                id="name"
                label={dialog.label && dialog.label.slice(0, -1)}
                type="text"
                fullWidth
                onChange={(e) => setInputValue(e.target.value)}
              />
            </>
          ) : (
            <></>
          )}
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setDialog({ open: false })}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() => {
              if (
                dialog.type === 'rootDomains' &&
                user?.userType !== 'globalAdmin'
              ) {
                if (dialog.stage === 0) {
                  // Start verification process
                  initiateDomainVerification(inputValue);
                  setDialog({ ...dialog, stage: 1 });
                  return;
                } else {
                  checkDomainVerification(inputValue);
                  return;
                }
              } else if (dialog.type && dialog.type !== 'tags') {
                if (inputValue) {
                  // Allow adding multiple values with a comma delimiter
                  organization[dialog.type].push(
                    ...inputValue.split(',').map((e) => e.trim())
                  );
                  setOrganization({ ...organization });
                }
              } else {
                if (tagValue) {
                  if (!organization.tags) organization.tags = [];
                  organization.tags.push(tagValue as any);
                  setOrganization({ ...organization });
                }
              }
              setDialog({ open: false });
              setInputValue('');
              setTagValue(null);
            }}
          >
            {dialog.type === 'rootDomains' && user?.userType !== 'globalAdmin'
              ? dialog.stage === 0
                ? 'Next'
                : 'Verify'
              : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
      <Grid container spacing={1} p={3}>
        <Grid item xs={12}>
          <TextField
            value={organization.name}
            disabled
            variant="standard"
            InputProps={{
              className: organizationClasses.orgName
            }}
          ></TextField>
        </Grid>
        <Grid item xs={12}>
          <ListInput label="Root Domains" type="rootDomains"></ListInput>
        </Grid>
        <Grid item xs={12}>
          <ListInput label="IP Blocks" type="ipBlocks"></ListInput>
        </Grid>
        {user?.userType === 'globalAdmin' && (
          <Grid item xs={12}>
            <ListInput label="Tags" type="tags"></ListInput>
          </Grid>
        )}
        <Grid item xs={12}>
          <Grid container spacing={1}>
            <Grid item xs={12} sm={3} lg={2} my={1}>
              <Typography variant="body2">Passive Mode</Typography>
            </Grid>
            <Grid item ml={-1}>
              <SwitchInput
                checked={organization.isPassive}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                  setOrganization({
                    ...organization,
                    isPassive: event.target.checked
                  });
                }}
                color="primary"
              />
            </Grid>
          </Grid>
        </Grid>
        <Grid item xs={12}>
          <Link to={`/organizations`}>
            <Button
              variant="outlined"
              style={{ marginRight: '10px', color: '#565C65' }}
            >
              Cancel
            </Button>
          </Link>
          <Button
            variant="contained"
            onClick={updateOrganization}
            style={{ background: '#565C65', color: 'white' }}
          >
            Save
          </Button>
        </Grid>
      </Grid>
    </Paper>,
    <React.Fragment key={1}>
      <h2>Org Members</h2>
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
