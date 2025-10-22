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
  useDateRange: boolean;
  startDate?: string;
  endDate?: string;
}

const MAX_SCAN_DAYS = Number(import.meta.env.VITE_MAX_SCAN_DAYS || 365);

export interface ScanArguments {
  start_datetime?: string;
  end_datetime?: string;
  [key: string]: any; // fallback for other dynamic args
}

// Helper: get UTC midnight string for X days ago
function getUTCDateMidnight(daysAgo: number): string {
  const date = new Date();
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCDate(date.getUTCDate() - daysAgo);
  return date.toISOString().slice(0, 16); // yyyy-MM-ddTHH:mm
}

// Helper: get current UTC datetime trimmed to minutes for datetime-local max attribute
function getUTCNowString(): string {
  const now = new Date();
  // zero-out seconds & ms so it matches datetime-local precision
  now.setUTCSeconds(0, 0);
  return now.toISOString().slice(0, 16); // yyyy-MM-ddTHH:mm
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
    arguments: scan ? scan.arguments : {},
    frequency: scan ? scan.frequency : 1,
    frequencyUnit: scan ? propValues.frequencyUnit : 'day',
    is_granular: scan ? scan.is_granular : false,
    is_user_modifiable: scan ? scan.is_user_modifiable : false,
    is_single_scan: scan ? scan.is_single_scan : false,
    organizations: scan ? propValues.organizations : [],
    tags: scan ? propValues.tags : [],
    concurrent_tasks: scan ? scan.concurrent_tasks : 1,
    useDateRange: !!(
      scan?.arguments?.start_datetime || scan?.arguments?.end_datetime
    ),
    startDate: scan?.arguments?.start_datetime || '',
    endDate: scan?.arguments?.end_datetime || ''
  });

  const [organizationOptions, setOrganizationOptions] =
    useState<OrganizationOption[]>(organizationOption);
  const [tagOptions, setTagOptions] = useState<OrganizationOption[]>([]);
  const [values, setValues] = useState<ScanFormValues>(setDefault());
  const [schemaUpdated, setSchemaUpdated] = useState<boolean>(false);
  const [dateRangeError, setDateRangeError] = useState<string>('');

  const onTextChange: React.ChangeEventHandler<
    HTMLInputElement | HTMLSelectElement
  > = (e) => {
    onChange(e.target.name, e.target.value);
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

  const setDefaultValues = useCallback(() => {
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
        is_single_scan:
          scan.is_single_scan ||
          !!(scan.arguments?.start_datetime || scan.arguments?.end_datetime),
        organizations: propValues.organizations,
        tags: propValues.tags,
        concurrent_tasks: scan.concurrent_tasks,
        useDateRange: !!(
          scan.arguments?.start_datetime || scan.arguments?.end_datetime
        ),
        startDate: scan.arguments?.start_datetime || '',
        endDate: scan.arguments?.end_datetime || ''
      }));
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

  // Clear date error when user adjusts start or end date
  useEffect(() => {
    if (values.useDateRange && dateRangeError) {
      setDateRangeError('');
    }
  }, [values.startDate, values.endDate]);

  return (
    <Form
      onSubmit={async (e) => {
        e.preventDefault();

        // Validate date range if used
        if (values.useDateRange) {
          if (!values.startDate || !values.endDate) {
            setDateRangeError('Please select both start and end date.');
            return;
          }

          const start = new Date(values.startDate);
          const end = new Date(values.endDate);
          const now = new Date();

          if (isNaN(start.getTime()) || isNaN(end.getTime())) {
            setDateRangeError('Invalid date format.');
            return;
          }

          if (start >= end) {
            setDateRangeError('Start date must be before end date.');
            return;
          }

          // Prevent future dates (end and start must be <= now)
          // Compare as UTC-aware dates: inputs are in local time but ISO strings created earlier are UTC
          // Here, we compare timestamps directly.
          if (
            start.getTime() > now.getTime() ||
            end.getTime() > now.getTime()
          ) {
            setDateRangeError('Dates cannot be in the future.');
            return;
          }

          // Ensure that (end - start) <= 365 days (align with backend)
          const diffDays =
            (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);
          if (diffDays > MAX_SCAN_DAYS) {
            setDateRangeError(
              `Date range cannot exceed ${MAX_SCAN_DAYS} days.`
            );
            return;
          }
        } else {
          setDateRangeError('');
        }

        await onSubmit({
          name: values.name,
          arguments: JSON.stringify({
            ...values.arguments,
            ...(values.useDateRange && {
              start_datetime: values.startDate
                ? new Date(values.startDate).toISOString()
                : null,
              end_datetime: values.endDate
                ? new Date(values.endDate).toISOString()
                : null
            })
          }),
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
      {type === 'create' && scanSchema && (
        <>
          <Label htmlFor="name">Name</Label>
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
              .map((i) => (
                <option key={i} value={i}>
                  {i}
                </option>
              ))}
          </Dropdown>
        </>
      )}

      {schemaUpdated && <p>{scanSchema[values.name].description}</p>}

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

      {values.name === 'vulnScanningSync' && (
        <>
          <Checkbox
            id="useDateRange"
            label="Limit scan to specific date range"
            name="useDateRange"
            checked={values.useDateRange}
            onChange={(e) => {
              onChange('useDateRange', e.target.checked);

              if (e.target.checked) {
                onChange('is_single_scan', true);

                // Default to 2 days ago → today (UTC midnight)
                const defaultStart = getUTCDateMidnight(2);
                const defaultEnd = getUTCDateMidnight(0);
                onChange('startDate', defaultStart);
                onChange('endDate', defaultEnd);
              } else {
                // Clear values when unchecked so they are not accidentally kept in state
                onChange('startDate', '');
                onChange('endDate', '');
                setDateRangeError('');
              }
            }}
          />
          {values.useDateRange && (
            <div className={classes.dateRangeContainer}>
              <Label htmlFor="startDate">Start Date (UTC)</Label>
              <TextInput
                id="startDate"
                name="startDate"
                type="datetime-local"
                value={values.startDate}
                onChange={(e) => onChange('startDate', e.target.value)}
                max={getUTCNowString()} // Prevent selecting future datetimes
              />
              <Label htmlFor="endDate">End Date (UTC)</Label>
              <TextInput
                id="endDate"
                name="endDate"
                type="datetime-local"
                value={values.endDate}
                onChange={(e) => onChange('endDate', e.target.value)}
                max={getUTCNowString()} // Prevent selecting future datetimes
              />
              {dateRangeError && (
                <p style={{ color: 'red' }}>{dateRangeError}</p>
              )}
            </div>
          )}
        </>
      )}

      <Checkbox
        id="is_single_scan"
        label="Run scan once"
        name="is_single_scan"
        checked={values.is_single_scan}
        disabled={values.useDateRange}
        onChange={(e) => onChange('is_single_scan', e.target.checked)}
      />
      {values.useDateRange && (
        <p style={{ color: 'red' }}>
          Must run once while limiting to a date range
        </p>
      )}

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
          onChange={(e) => onChange(e.target.name, Number(e.target.value))}
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
