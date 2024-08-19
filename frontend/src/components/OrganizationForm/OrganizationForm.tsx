import React, { useCallback, useEffect, useState } from 'react';
import * as orgFormStyles from './orgFormStyle';
import { Organization, OrganizationTag } from 'types';
import {
  Autocomplete,
  Button,
  Chip,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  MenuItem,
  Select,
  Switch,
  TextField,
  Typography
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import {
  STATE_ABBREVIATED_OPTIONS,
  STATE_OPTIONS
} from '../../constants/constants';
import { useAuthContext } from 'context';

const StyledDialog = orgFormStyles.StyledDialog;

interface AutocompleteType extends Partial<OrganizationTag> {
  title?: string;
}

export interface OrganizationFormValues {
  name: string;
  rootDomains: string;
  ipBlocks: string;
  isPassive: boolean;
  tags: { name: string }[];
  stateName?: string | null | undefined;
  acronym?: string | null;
  state?: string | null;
}

const getStateAbbreviation = (stateName: string | null): string | undefined => {
  if (stateName) {
    const index = STATE_OPTIONS.indexOf(stateName);
    if (index !== -1) {
      return STATE_ABBREVIATED_OPTIONS[index];
    }
  }
  return '';
};

export const OrganizationForm: React.FC<{
  organization?: Organization;
  open: boolean;
  setOpen: (open: boolean) => void;
  onSubmit: (values: Object) => Promise<void>;
  type: string;
  parent?: Organization;
  chosenTags: string[];
  setChosenTags: Function;
}> = ({
  organization,
  onSubmit,
  type,
  open,
  setOpen,
  parent,
  chosenTags,
  setChosenTags
}) => {
  const defaultValues = () => ({
    name: organization ? organization.name : '',
    rootDomains: organization ? organization.rootDomains.join(', ') : '',
    ipBlocks: organization ? organization.ipBlocks.join(', ') : '',
    isPassive: organization ? organization.isPassive : false,
    tags: [],
    stateName: organization ? organization.stateName : '',
    acronym: organization ? organization.acronym : ''
  });

  const [values, setValues] = useState<OrganizationFormValues>(defaultValues);
  const [tags, setTags] = useState<AutocompleteType[]>([]);
  const [formErrors, setFormErrors] = useState({
    name: false,
    acronym: false,
    rootDomains: false,
    stateName: false
  });
  const { apiGet } = useAuthContext();

  const fetchTags = useCallback(async () => {
    try {
      const tags = await apiGet<OrganizationTag[]>(`/organizations/tags`);
      setTags(tags);
    } catch (e) {
      console.error(e);
    }
  }, [apiGet]);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
  > = (e) => onChange(e.target.name, e.target.value);

  const validateForm = (values: OrganizationFormValues) => {
    const newFormErrors = {
      name: values.name.trim() === '',
      acronym: values.acronym?.trim() === '',
      rootDomains: values.rootDomains.trim() === '',
      stateName: values.stateName?.trim() === ''
    };
    setFormErrors(newFormErrors);
    return !Object.values(newFormErrors).some((error) => error);
  };

  const onChange = (name: string, value: any) => {
    setValues((values) => ({
      ...values,
      [name]: value
    }));
  };
  const handleStateChange = (event: SelectChangeEvent<string | null>) => {
    setValues((values) => ({
      ...values,
      [event.target.name]: event.target.value,
      state: getStateAbbreviation(event.target.value)
    }));
  };

  const handleTagChange = (event: any, newValue: string[]) => {
    setChosenTags(newValue);
    setValues((prevValues) => ({
      ...prevValues,
      tags: newValue.map((tag) => ({ name: tag }))
    }));
  };

  const textFieldStyling = {
    '& .MuiOutlinedInput-root': {
      '&.Mui-focused fieldset': {
        borderRadius: '0px'
      }
    }
  };

  return (
    <StyledDialog
      open={open}
      onClose={() => setOpen(false)}
      aria-labelledby="form-dialog-title"
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle id="form-dialog-title">
        Create New {parent ? 'Team' : 'Organization'}
      </DialogTitle>
      <DialogContent>
        Organization Name
        <TextField
          sx={textFieldStyling}
          placeholder="Enter the Organization's Name"
          size="small"
          margin="dense"
          id="name"
          inputProps={{ maxLength: 250 }}
          name="name"
          type="text"
          fullWidth
          value={values.name}
          onChange={onTextChange}
          error={formErrors.name}
          helperText={formErrors.name && 'Organization Name is required'}
        />
        Organization Acronym
        <TextField
          sx={textFieldStyling}
          placeholder="Enter a unique Acronym for the Organization"
          size="small"
          margin="dense"
          id="acronym"
          inputProps={{ maxLength: 250 }}
          name="acronym"
          type="text"
          fullWidth
          value={values.acronym}
          onChange={onTextChange}
          error={formErrors.acronym}
          helperText={formErrors.acronym && 'Organization Acronym is required'}
        />
        Root Domains
        <TextField
          sx={textFieldStyling}
          placeholder="Enter Root Domains, comma separated"
          size="small"
          margin="dense"
          id="rootDomains"
          name="rootDomains"
          type="text"
          fullWidth
          value={values.rootDomains}
          onChange={onTextChange}
          error={formErrors.rootDomains}
          helperText={
            formErrors.rootDomains && 'At least one Root Domain is required'
          }
        />
        IP Blocks
        <TextField
          sx={textFieldStyling}
          placeholder="Enter IP Blocks, comma separated"
          size="small"
          margin="dense"
          id="ipBlocks"
          name="ipBlocks"
          type="text"
          fullWidth
          value={values.ipBlocks}
          onChange={onTextChange}
        />
        Organization State
        <Select
          sx={{ mt: 1 }}
          displayEmpty
          size="small"
          id="stateName"
          value={values.stateName}
          name="stateName"
          onChange={handleStateChange}
          fullWidth
          renderValue={
            values.stateName !== ''
              ? undefined
              : () => (
                  <Typography color="#bdbdbd">
                    Select a US State or Territory
                  </Typography>
                )
          }
          error={formErrors.stateName}
        >
          {STATE_OPTIONS.map((stateName: string, index: number) => (
            <MenuItem key={index} value={stateName}>
              {stateName}
            </MenuItem>
          ))}
        </Select>
        {formErrors.stateName && (
          <Typography pl={2} variant="caption" color="error.main">
            Organization State is required
            <br />
          </Typography>
        )}
        <Autocomplete
          sx={{ mt: 1 }}
          multiple
          options={tags
            .map((option) => option.name)
            .filter((name): name is string => name !== undefined)}
          freeSolo
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
          renderInput={(params) => (
            <TextField {...params} placeholder="Select or add tags" />
          )}
        />
        <Typography variant="caption">
          Select an existing tag or type and press enter to add a new one.
        </Typography>
        <br />
        <FormControlLabel
          sx={{ mt: 1 }}
          control={
            <Switch
              checked={values.isPassive}
              name="isPassive"
              onChange={(e) => {
                onChange(e.target.name, e.target.checked);
              }}
              color="primary"
            />
          }
          label="Passive Mode"
        />
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={() => setOpen(false)}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={async () => {
            if (!validateForm(values)) {
              return;
            }
            await onSubmit({
              rootDomains:
                values.rootDomains === ''
                  ? []
                  : values.rootDomains
                      .split(',')
                      .map((domain) => domain.trim()),
              ipBlocks:
                values.ipBlocks === ''
                  ? []
                  : values.ipBlocks.split(',').map((ip) => ip.trim()),
              name: values.name,
              stateName: values.stateName,
              state: values.state,
              isPassive: values.isPassive,
              tags: values.tags,
              acronym: values.acronym,
              parent: parent ? parent.id : undefined
            });
            if (!organization) setValues(defaultValues);
            setOpen(false);
          }}
        >
          Save
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};
