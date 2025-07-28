import React, { useState, useEffect, useCallback } from 'react';
import classes from './styles.module.scss';
import { OrganizationTag, Scan, ScanSchema } from 'types';
import {
  Button,
  Form,
  Dropdown,
  TextInput,
  Checkbox,
  Label
} from '@trussworks/react-uswds';
import MultiSelect from 'pages/Scans/MultiSelect';
import { OrganizationOption } from 'pages/Scans/ScansView';
import { Link } from 'react-router-dom';

export interface ScanFormValues {
  name: string;
  organizations: OrganizationOption[];
  tags: OrganizationOption[];
  arguments: any;
  frequency: number;
  frequencyUnit: string;
  is_granular: boolean;
  is_user_modifiable: boolean;
  is_single_scan: boolean;
  concurrent_tasks: number;
}

export const ScanForm: React.FC<{
  propValues: ScanFormValues;
  organizationOption: OrganizationOption[];
  tags: OrganizationTag[];
  global?: any;
  onSubmit: (values: any) => Promise<void>;
  type: 'create' | 'edit';
  scan?: Scan;
  scanSchema: ScanSchema;
}> = ({
  propValues,
  organizationOption,
  tags,
  global,
  onSubmit,
  type,
  scan,
  scanSchema
}) => {
  const setDefault = () => ({
    name: scan ? scan.name : 'censys',
    arguments: scan ? scan.arguments : '{}',
    frequency: scan ? scan.frequency : 1,
    frequencyUnit: scan ? propValues.frequencyUnit : 'day',
    is_granular: scan ? scan.is_granular : false,
    is_user_modifiable: scan ? scan.is_user_modifiable : false,
    is_single_scan: scan ? scan.is_single_scan : false,
    organizations: scan ? propValues.organizations : [],
    tags: scan ? propValues.tags : [],
    concurrent_tasks: scan ? scan.concurrent_tasks : 1
  });
  const [organizationOptions, setOrganizationOptions] =
    useState<OrganizationOption[]>(organizationOption);
  const [tagOptions, setTagOptions] = useState<OrganizationOption[]>([]);
  const [values, setValues] = useState<ScanFormValues>(setDefault());
  const [schemaUpdated, setSchemaUpdated] = useState<boolean>(false);

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement
  > = (e) => {
    onChange(e.target.name, e.target.value);
    //Ensures global scans can't be granular
    if (type === 'create' && scanSchema[e.target.value]) {
      onChange('is_granular', false);
    }
  };

  const onChange = (name: string, value: any) => {
    setValues((values) => ({
      ...values,
      [name]: value
    }));
  };

  const setDefaultValues = useCallback(async () => {
    try {
      setOrganizationOptions(organizationOption);
      setTagOptions(tags.map((tag) => ({ label: tag.name, value: tag.id })));
      if (scanSchema && scanSchema[values.name]) {
        setSchemaUpdated(true);
      }
      if (scan) {
        setValues((values) => ({
          ...values,
          name: scan.name,
          frequency: propValues.frequency,
          frequencyUnit: propValues.frequencyUnit,
          is_granular: scan.is_granular,
          is_user_modifiable: scan.is_user_modifiable,
          is_single_scan: scan.is_single_scan,
          organizations: propValues.organizations,
          tags: propValues.tags,
          concurrent_tasks: scan.concurrent_tasks
        }));
      }
    } catch (e) {
      console.error(e);
    }
  }, [
    organizationOption,
    propValues.frequency,
    propValues.frequencyUnit,
    propValues.organizations,
    propValues.tags,
    tags,
    scan,
    scanSchema,
    values.name
  ]);

  useEffect(() => {
    setDefaultValues();
  }, [setDefaultValues]);

  return (
    <Form
      onSubmit={async (e) => {
        e.preventDefault();
        await onSubmit({
          name: values.name,
          arguments: values.arguments,
          organizations: values.organizations,
          tags: values.tags,
          frequency: values.frequency,
          frequencyUnit: values.frequencyUnit,
          is_granular: values.is_granular,
          is_user_modifiable: values.is_user_modifiable,
          is_single_scan: values.is_single_scan,
          concurrent_tasks: values.concurrent_tasks
        });
      }}
      className={classes.form}
    >
      {type === 'create' &&
        scanSchema && <Label htmlFor="name">Name</Label> && (
          <Dropdown
            aria-label="Select scan dropdown"
            required
            id="name"
            name="name"
            className={classes.textField}
            onChange={onTextChange}
            value={values.name}
          >
            {Object.keys(scanSchema)
              .sort((a, b) => a.localeCompare(b))
              .map((i) => {
                return (
                  <option key={i} value={i}>
                    {i}
                  </option>
                );
              })}
          </Dropdown>
        )}
      {schemaUpdated && <p>{scanSchema[values.name].description}</p>}
      {/* <Label htmlFor="arguments">Arguments</Label>
        <TextInput
          required
          id="arguments"
          name="arguments"
          className={classes.textField}
          type="text"
          value={values.arguments}
          onChange={onTextChange}
        /> */}
      {(values.name === 'censysIpv4' ||
        values.name === 'censysCertificates' ||
        (schemaUpdated && !scanSchema[values.name].global) ||
        !global) && (
        <Checkbox
          id="is_granular"
          label="Limit enabled organizations"
          name="is_granular"
          checked={values.is_granular}
          onChange={(e) => {
            onChange('is_granular', e.target.checked);
            if (!e.target.checked) {
              // Only granular scans can be user-modifiable.
              onChange('is_user_modifiable', false);
            }
          }}
        />
      )}
      {values.is_granular && (
        <>
          <Label htmlFor="organizations">Enabled Organizations</Label>
          <MultiSelect
            name="organizations"
            options={organizationOptions}
            value={values.organizations}
            onChange={(e) => onChange('organizations', e)}
            zIndex={100}
          />
          <Label htmlFor="tags">Enabled Organization Tags</Label>
          <MultiSelect
            name="tags"
            options={tagOptions}
            value={values.tags}
            onChange={(e) => onChange('tags', e)}
            zIndex={99}
          />
          <br />
        </>
      )}
      {values.is_granular && (
        <>
          <Checkbox
            id="is_user_modifiable"
            label="Allow any organization's admins to toggle this scan on/off"
            name="is_user_modifiable"
            checked={values.is_user_modifiable}
            onChange={(e) => onChange('is_user_modifiable', e.target.checked)}
          />
          <br />
        </>
      )}
      <Checkbox
        id="is_single_scan"
        label="Run scan once"
        name="is_single_scan"
        checked={values.is_single_scan}
        onChange={(e) => onChange('is_single_scan', e.target.checked)}
      />
      {!values.is_single_scan && (
        <div className="form-group form-inline">
          <label style={{ marginRight: '10px' }} htmlFor="frequency">
            Run every
          </label>
          <TextInput
            id="frequency"
            maxLength={250}
            name="frequency"
            type="number"
            style={{
              display: 'inline-block',
              width: '150px',
              marginRight: '15px'
            }}
            value={values.frequency}
            onChange={(e) => {
              onChange(e.target.name, Number(e.target.value));
            }}
          />
          <Dropdown
            aria-label="Select frequency unit dropdown"
            id="frequencyUnit"
            name="frequencyUnit"
            onChange={onTextChange}
            value={values.frequencyUnit}
            style={{ display: 'inline-block', width: '150px' }}
          >
            <option value="hour">Hour(s)</option>
            <option value="day">Day(s)</option>
          </Dropdown>
        </div>
      )}
      <div className="form-group">
        <Label htmlFor="concurrent_tasks">Number of Concurrent Tasks</Label>
        <TextInput
          id="concurrent_tasks"
          maxLength={250}
          name="concurrent_tasks"
          type="number"
          className={classes.textField}
          style={{ width: '150px' }}
          value={values.concurrent_tasks}
          onChange={(e) => {
            onChange(e.target.name, Number(e.target.value));
          }}
        />
        <span
          className="usa-hint"
          style={{ marginTop: '0.5rem', display: 'block' }}
        >
          {schemaUpdated
            ? scanSchema[values.name].max_concurrent_tasks
              ? `This scan allows a maximum of ${
                  scanSchema[values.name].max_concurrent_tasks
                } concurrent scans`
              : 'This scan allows no limit of concurrent tasks'
            : 'This scan allows a maximum of 10 concurrent scans'}
        </span>
      </div>
      <br />
      {type === 'edit' && (
        <Link to={`/admin-tools`}>
          <Button type="button" outline>
            {' '}
            Return to Scans
          </Button>
        </Link>
      )}
      <Button type="submit" color="secondary.main">
        {type === 'edit' ? 'Save Changes' : 'Create Scan'}
      </Button>
    </Form>
  );
};
