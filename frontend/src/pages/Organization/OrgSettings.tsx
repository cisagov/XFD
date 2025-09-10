import React, { useState } from 'react';
import { useAuthContext } from 'context';
import {
  PendingDomain,
  Organization as OrganizationType,
  OrganizationTag
} from 'types';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Grid,
  Stack,
  Switch,
  TextField,
  Typography
} from '@mui/material';
import { CheckCircleOutline, Place, Public } from '@mui/icons-material';
import InfoDialog from 'components/Dialog/InfoDialog';
import ListInput from './ListInput';

interface AutocompleteType extends Partial<OrganizationTag> {
  title?: string;
}

interface OrgSettingsType extends Partial<OrganizationType> {
  id: any;
  granular_scans: any;
  root_domains: string[];
  ip_blocks: string[];
  tags: OrganizationTag[];
  pending_domains: PendingDomain[];
}

type OrgSettingsProps = {
  organization: OrgSettingsType;
  setOrganization: Function;
  tags: AutocompleteType[];
};

export const OrgSettings: React.FC<OrgSettingsProps> = ({
  organization,
  setOrganization,
  tags
}) => {
  const { apiPut, apiPost, user, setFeedbackMessage } = useAuthContext();
  const [inputValue, setInputValue] = useState('');
  const [dialog, setDialog] = useState<{
    open: boolean;
    type?: string;
    label?: string;
    stage?: number;
    domainVerificationStatusMessage?: string;
  }>({ open: false });
  const [isSaveDisabled, setIsSaveDisabled] = useState(true);
  const [infoDialogOpen, setInfoDialogOpen] = useState(false);
  const [chosenTags, setChosenTags] = useState(
    () => organization.tags?.map((t) => t.name) || []
  );
  const [localTags, setLocalTags] = useState(chosenTags);

  const updateOrganization = async () => {
    try {
      const org = await apiPut(`/organizations/${organization.id}`, {
        body: organization
      });
      setOrganization(org);
      setFeedbackMessage({
        message: 'Organization successfully updated',
        type: 'success'
      });
      setInfoDialogOpen(true);
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422
            ? 'Error updating organization'
            : e.message || e.toString(),
        type: 'error'
      });
      console.error(e);
    }
  };

  const initiateDomainVerification = async (domain: string) => {
    try {
      const pending_domains = await apiPost(
        `/organizations/${organization.id}/initiateDomainVerification`,
        { body: { domain } }
      );
      setOrganization({ ...organization, pending_domains });
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422
            ? 'Error creating domain'
            : e.message || e.toString(),
        type: 'error'
      });
      console.error(e);
    }
  };

  const checkDomainVerification = async (domain: string) => {
    try {
      const resp = await apiPost(
        `/organizations/${organization.id}/checkDomainVerification`,
        { body: { domain } }
      );
      if (resp.success && resp.organization) {
        setOrganization(resp.organization);
        setDialog({ open: false });
        setFeedbackMessage({
          message: `Domain ${inputValue} successfully verified!`,
          type: 'success'
        });
      } else {
        setDialog((prev) => ({
          ...prev,
          domainVerificationStatusMessage:
            'Record not yet found. DNS records may take up to 72 hours to propagate.'
        }));
      }
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422
            ? 'Error verifying domain'
            : e.message || e.toString(),
        type: 'error'
      });
      console.error(e);
    }
  };

  const handleDialogSubmit = async () => {
    if (dialog.type === 'root_domains' && user?.user_type !== 'globalAdmin') {
      if (dialog.stage === 0) {
        await initiateDomainVerification(inputValue);
        setDialog({ ...dialog, stage: 1 });
      } else {
        await checkDomainVerification(inputValue);
      }
      return;
    }
    if (dialog.type === 'tags') {
      setChosenTags(localTags);
      setOrganization((prev: any) => ({
        ...prev,
        tags: localTags.map((name: any) => ({ name }))
      }));
      setIsSaveDisabled(false);
      setLocalTags(localTags);
    } else if (dialog.type && inputValue) {
      const key = dialog.type as keyof OrgSettingsType;
      const updated = [
        ...(organization[key] as string[]),
        ...inputValue.split(',').map((e) => e.trim())
      ];
      setOrganization({ ...organization, [key]: updated });
    }
    setDialog({ open: false });
    setInputValue('');
    setIsSaveDisabled(false);
  };

  const renderDialogContent = () => {
    switch (dialog.type) {
      case 'tags':
        return (
          <>
            <DialogContentText>
              Use the dropdown to select or deselect existing tags. Type and
              press enter to add new ones.
            </DialogContentText>
            <Autocomplete
              value={localTags}
              onChange={(_, value) => {
                setLocalTags(
                  value.filter((v): v is string => typeof v === 'string')
                );
              }}
              multiple
              freeSolo
              options={tags.map((t) => t.name).filter(Boolean)}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((tag, i) => {
                    if (tag) {
                      return (
                        <Chip key={tag + i} label={tag} variant="outlined" />
                      );
                    }
                    return <></>;
                  })}
                </Box>
              )}
              renderInput={(params) => (
                <TextField {...params} placeholder="Select or add tags" />
              )}
              sx={{ mt: 1 }}
            />
          </>
        );
      case 'root_domains':
        if (dialog.stage === 1) {
          return (
            <>
              <DialogContentText>
                Add the TXT record below to {inputValue}&apos;s DNS and click
                Verify.
              </DialogContentText>
              <TextField
                fullWidth
                value={
                  organization.pending_domains.find(
                    (d) => d.name === inputValue
                  )?.token || ''
                }
                onFocus={(e) => e.target.select()}
              />
              {dialog.domainVerificationStatusMessage && (
                <DialogContentText mt={4}>
                  {dialog.domainVerificationStatusMessage}
                </DialogContentText>
              )}
            </>
          );
        }
        return (
          <>
            <DialogContentText>
              Enter a domain to begin verification.
            </DialogContentText>
            <TextField
              autoFocus
              fullWidth
              label="Domain"
              onChange={(e) => setInputValue(e.target.value)}
            />
          </>
        );
      default:
        return (
          <TextField
            autoFocus
            fullWidth
            placeholder={`Enter ${dialog.label?.slice(0, -1)}(s)`}
            onChange={(e) => setInputValue(e.target.value)}
          />
        );
    }
  };

  return (
    <>
      <Dialog
        open={dialog.open}
        onClose={(event, reason) => {
          if (reason !== 'backdropClick') {
            setDialog({ open: false });
          }
        }}
        disableEscapeKeyDown
        aria-labelledby="form-dialog-title"
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>
          {dialog.type === 'tags' ? 'Update ' : 'Add '}
          {dialog.label?.slice(0, -1)}(s)
        </DialogTitle>
        <DialogContent>{renderDialogContent()}</DialogContent>
        <DialogActions>
          <Button
            variant="outlined"
            onClick={() => {
              if (dialog.type === 'tags') {
                const currentTagNames =
                  organization.tags?.map((tag) => tag.name) ?? [];
                setLocalTags(currentTagNames);
              }
              setDialog({ open: false });
            }}
          >
            Cancel
          </Button>
          <Button variant="contained" onClick={handleDialogSubmit}>
            {dialog.type === 'tags' ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>

      <InfoDialog
        isOpen={infoDialogOpen}
        handleClick={() => {
          setInfoDialogOpen(false);
          setIsSaveDisabled(true);
        }}
        icon={<CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />}
        title={<Typography variant="h4">Success</Typography>}
        content={
          <Typography>{organization.name} was successfully updated.</Typography>
        }
      />
      <Grid container spacing={1} p={3}>
        <Grid size={{ xs: 12 }}>
          <TextField
            fullWidth
            value={organization.name}
            disabled
            variant="standard"
            slotProps={{
              htmlInput: {
                sx: { fontSize: '18px', fontWeight: 400 }
              }
            }}
          />
        </Grid>
        <Grid size={{ xs: 12 }} mt={2} mb={1}>
          <Stack direction="row" alignItems="center" spacing={1}>
            {organization.region_id && (
              <>
                <Public sx={{ color: 'gray' }} />
                <Typography variant="body1" color="gray">
                  Region {organization.region_id}
                </Typography>
              </>
            )}
            {(organization.state_name || organization.state) && (
              <>
                <Place sx={{ color: 'gray' }} />
                <Typography variant="body1" color="gray">
                  {organization.state_name || organization.state}
                </Typography>
              </>
            )}
          </Stack>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <ListInput
            label="Root Domains"
            type="root_domains"
            disableAddButton
            disableDelete
            organization={organization}
            userType={user?.user_type}
            setOrganization={setOrganization}
            setDialog={setDialog}
            setInputValue={setInputValue}
            setIsSaveDisabled={setIsSaveDisabled}
          />
        </Grid>
        <Grid size={{ xs: 12 }}>
          <ListInput
            label="IP Blocks"
            type="ip_blocks"
            disableAddButton
            disableDelete
            organization={organization}
            userType={user?.user_type}
            setOrganization={setOrganization}
            setDialog={setDialog}
            setInputValue={setInputValue}
            setIsSaveDisabled={setIsSaveDisabled}
          />
        </Grid>
        {user?.user_type === 'globalAdmin' && (
          <Grid size={{ xs: 12 }}>
            <ListInput
              label="Tags"
              type="tags"
              disableAddButton
              disableDelete
              organization={organization}
              userType={user?.user_type}
              setOrganization={setOrganization}
              setDialog={setDialog}
              setInputValue={setInputValue}
              setIsSaveDisabled={setIsSaveDisabled}
              chosenTags={chosenTags}
              setChosenTags={setChosenTags}
              localTags={localTags}
              setLocalTags={setLocalTags}
            />
          </Grid>
        )}
        <Grid size={{ xs: 12 }}>
          <Grid container spacing={1}>
            <Grid size={{ xs: 12, sm: 3, lg: 2 }} my={1}>
              <Typography variant="body2">Passive Mode</Typography>
            </Grid>
            <Grid ml={-1}>
              <Switch
                checked={organization.is_passive}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                  setOrganization({
                    ...organization,
                    is_passive: event.target.checked
                  });
                  if (!organization.is_passive) {
                    setIsSaveDisabled(false);
                  }
                }}
                color="primary"
                disabled={user?.user_type === 'globalView'}
                slotProps={{
                  input: {
                    'aria-label': 'Toggle passive mode',
                    role: 'switch'
                  }
                }}
              />
            </Grid>
          </Grid>
        </Grid>
        {organization.root_domains.length === 0 && (
          <Grid size={{ xs: 12 }}>
            <Alert severity="error">
              An organization must have at least one Root Domain.
            </Alert>
          </Grid>
        )}
        <Grid size={{ xs: 12 }} mt={2}>
          <Button variant="outlined" sx={{ mr: 1 }} href="/organizations">
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={updateOrganization}
            disabled={
              organization.root_domains.length === 0 ||
              isSaveDisabled ||
              user?.user_type === 'globalView'
            }
          >
            Save
          </Button>
        </Grid>
      </Grid>
    </>
  );
};

export default OrgSettings;
