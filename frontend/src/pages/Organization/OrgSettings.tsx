import React from 'react';
import { useAuthContext } from 'context';
import {
  PendingDomain,
  Organization as OrganizationType,
  OrganizationTag
} from 'types';
import {
  Alert,
  Autocomplete,
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

interface AutocompleteType extends Partial<OrganizationTag> {
  title?: string;
}

interface OrgSettingsType extends Partial<OrganizationType> {
  id: any;
  granularScans: any;
  rootDomains: string[];
  ipBlocks: string[];
  tags: OrganizationTag[];
  pendingDomains: PendingDomain[];
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
  const [inputValue, setInputValue] = React.useState('');
  const [dialog, setDialog] = React.useState<{
    open: boolean;
    type?: 'rootDomains' | 'ipBlocks' | 'tags';
    label?: string;
    stage?: number;
    domainVerificationStatusMessage?: string;
  }>({ open: false });
  const [isSaveDisabled, setIsSaveDisabled] = React.useState(true);
  const [infoDialogOpen, setInfoDialogOpen] = React.useState(false);
  const [chosenTags, setChosenTags] = React.useState<string[]>(
    organization.tags ? organization.tags.map((tag) => tag.name) : []
  );

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
      setInfoDialogOpen(true);
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

  const handleTagChange = (event: any, newValue: any) => {
    setChosenTags(newValue);
    setOrganization((prevValues: any) => ({
      ...prevValues,
      tags: newValue.map((tag: any) => ({ name: tag }))
    }));
    setIsSaveDisabled(false);
  };

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
                label={typeof value === 'string' ? value : value.name}
                onDelete={() => {
                  organization[props.type].splice(index, 1);
                  setOrganization({ ...organization });
                  if (chosenTags.length > 0) {
                    chosenTags.splice(index, 1);
                    setChosenTags(chosenTags);
                  }
                  setIsSaveDisabled(false);
                }}
              ></Chip>
            </Grid>
          ))}
        {props.type === 'rootDomains' &&
          organization.pendingDomains.map((domain, index: number) => (
            <Grid item mb={1} key={index}>
              <Chip
                sx={{ backgroundColor: '#C4C4C4' }}
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
  return (
    <>
      <Dialog
        open={dialog.open}
        onClose={() => setDialog({ open: false })}
        aria-labelledby="form-dialog-title"
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle id="form-dialog-title">
          Add {dialog.label && dialog.label.slice(0, -1)}(s)
        </DialogTitle>
        <DialogContent>
          {dialog.type === 'tags' ? (
            <>
              <DialogContentText>
                Select or deselect an existing tag or type and press enter to
                add a new one.
              </DialogContentText>
              <Autocomplete
                value={chosenTags}
                onChange={handleTagChange}
                renderTags={(value: readonly string[], getTagProps) =>
                  value.map((option: string, index: number) => {
                    const { key, ...tagProps } = getTagProps({ index });
                    return (
                      <Chip
                        variant="outlined"
                        label={option}
                        key={key}
                        {...tagProps}
                      />
                    );
                  })
                }
                sx={{ mt: 1 }}
                multiple
                options={tags
                  .map((option) => option.name)
                  .filter((name): name is string => name !== undefined)}
                freeSolo
                renderInput={(params) => (
                  <TextField {...params} placeholder="Select or add tags" />
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
                sx={{ width: '100%' }}
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
                placeholder={
                  dialog.label && 'Enter ' + dialog.label.slice(0, -1) + '(s)'
                }
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
                  if (organization.rootDomains.length !== 0) {
                    setIsSaveDisabled(false);
                  }
                }
              }
              setDialog({ open: false });
              setInputValue('');
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
      <InfoDialog
        isOpen={infoDialogOpen}
        handleClick={() => {
          setInfoDialogOpen(false);
          setIsSaveDisabled(true);
        }}
        icon={<CheckCircleOutline color="success" sx={{ fontSize: '80px' }} />}
        title={<Typography variant="h4">Success </Typography>}
        content={
          <Typography variant="body1">
            {organization.name} was successfully updated.
          </Typography>
        }
      />
      <Grid container spacing={1} p={3}>
        <Grid item xs={12}>
          <TextField
            fullWidth
            value={organization.name}
            disabled
            variant="standard"
            InputProps={{
              sx: { fontSize: '18px', fontWeight: 400 }
            }}
          ></TextField>
        </Grid>
        <Grid item xs={12} mt={2} mb={1}>
          <Stack direction="row" alignItems="center" spacing={1}>
            {organization.regionId && (
              <>
                <Public sx={{ color: 'gray' }} />
                <Typography variant="body1" color="gray">
                  Region {organization && organization.regionId}
                </Typography>
              </>
            )}
            {(organization.stateName || organization.state) && (
              <>
                <Place sx={{ color: 'gray' }} />
                <Typography variant="body1" color="gray">
                  {organization &&
                    (organization.stateName || organization.state)}
                </Typography>
              </>
            )}
          </Stack>
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
              <Switch
                checked={organization.isPassive}
                onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                  setOrganization({
                    ...organization,
                    isPassive: event.target.checked
                  });
                  if (!organization.isPassive) {
                    setIsSaveDisabled(false);
                  }
                }}
                color="primary"
              />
            </Grid>
          </Grid>
        </Grid>
        {organization.rootDomains.length === 0 && (
          <Grid item xs={12}>
            <Alert severity="error">
              An organization must have at least one Root Domain.
            </Alert>
          </Grid>
        )}
        <Grid item xs={12} mt={2}>
          <Button variant="outlined" sx={{ mr: 1 }} href="/organizations">
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={updateOrganization}
            disabled={organization.rootDomains.length === 0 || isSaveDisabled}
          >
            Save
          </Button>
        </Grid>
      </Grid>
    </>
  );
};

export default OrgSettings;
