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
import { STATE_ABBREVIATED_OPTIONS, STATE_OPTIONS } from 'constants/constants';
import { useAuthContext } from 'context';

const StyledDialog = orgFormStyles.StyledDialog;

interface AutocompleteType extends Partial<OrganizationTag> {
  title?: string;
}

export interface OrganizationFormValues {
  name: string;
  root_domains: string;
  ip_blocks: string;
  is_passive: boolean;
  tags: { name: string }[];
  state_name?: string | null | undefined;
  acronym?: string | null;
  state?: string | null;
}

const getStateAbbreviation = (
  state_name: string | null
): string | undefined => {
  if (state_name) {
    const index = STATE_OPTIONS.indexOf(state_name);
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
    root_domains: organization ? organization.root_domains.join(', ') : '',
    ip_blocks: organization ? organization.ip_blocks.join(', ') : '',
    is_passive: organization ? organization.is_passive : false,
    tags: [],
    state_name: organization ? organization.state_name : '',
    acronym: organization ? organization.acronym : ''
  });

  const [values, setValues] = useState<OrganizationFormValues>(defaultValues);
  const [tags, setTags] = useState<AutocompleteType[]>([]);
  const [formErrors, setFormErrors] = useState({
    name: false,
    acronym: false,
    root_domains: false,
    state_name: false
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
      root_domains: values.root_domains.trim() === '',
      state_name: values.state_name?.trim() === ''
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

  const handleTagChange = (event: any, new_value: string[]) => {
    setChosenTags(new_value);
    setValues((prevValues) => ({
      ...prevValues,
      tags: new_value.map((tag) => ({ name: tag }))
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
          slotProps={{ htmlInput: { maxLength: 250 } }}
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
          slotProps={{ htmlInput: { maxLength: 250 } }}
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
          id="root_domains"
          name="root_domains"
          type="text"
          fullWidth
          value={values.root_domains}
          onChange={onTextChange}
          error={formErrors.root_domains}
          helperText={
            formErrors.root_domains && 'At least one Root Domain is required'
          }
        />
        IP Blocks
        <TextField
          sx={textFieldStyling}
          placeholder="Enter IP Blocks, comma separated"
          size="small"
          margin="dense"
          id="ip_blocks"
          name="ip_blocks"
          type="text"
          fullWidth
          value={values.ip_blocks}
          onChange={onTextChange}
        />
        Organization State
        <Select
          sx={{ mt: 1 }}
          displayEmpty
          size="small"
          id="state_name"
          value={values.state_name}
          name="state_name"
          onChange={handleStateChange}
          fullWidth
          renderValue={
            values.state_name !== ''
              ? undefined
              : () => (
                  <Typography color="#bdbdbd">
                    Select a US State or Territory
                  </Typography>
                )
          }
          error={formErrors.state_name}
        >
          {STATE_OPTIONS.map((state_name: string, index: number) => (
            <MenuItem key={index} value={state_name}>
              {state_name}
            </MenuItem>
          ))}
        </Select>
        {formErrors.state_name && (
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
          renderValue={(value: readonly string[], getTagProps) =>
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
              checked={values.is_passive}
              name="is_passive"
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
              root_domains:
                values.root_domains === ''
                  ? []
                  : values.root_domains
                      .split(',')
                      .map((domain) => domain.trim()),
              ip_blocks:
                values.ip_blocks === ''
                  ? []
                  : values.ip_blocks.split(',').map((ip) => ip.trim()),
              name: values.name,
              state_name: values.state_name,
              state: values.state,
              is_passive: values.is_passive,
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
