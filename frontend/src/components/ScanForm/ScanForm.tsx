import React, { useState, useEffect, useCallback } from 'react';

// Material-UI Components
import Autocomplete from '@mui/material/Autocomplete';
import Box from '@mui/material/Box';
import MuiButton from '@mui/material/Button';
import MuiCheckbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormHelperText from '@mui/material/FormHelperText';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

// Pages
import { OrganizationOption } from '@/types/organization';

// Types
import { Scan, ScanSchema } from '@/types';

export interface ScanFormValues {
  name: string;
  organizations: OrganizationOption[];
  // Tag selection is currently unused. This code is retained for potential future restoration.
  // tags: OrganizationOption[];
  arguments: any;
  frequency: number;
  frequencyUnit: string;
  is_granular: boolean;
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
  // tags: OrganizationTag[];
  global?: any;
  onSubmit: (values: any) => Promise<void>;
  type: 'create' | 'edit';
  scan?: Scan;
  scanSchema: ScanSchema;
}> = ({
  propValues,
  organizationOption,
  // tags,
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
      is_single_scan: scan ? scan.is_single_scan : false,
      organizations: scan ? propValues.organizations : [],
      // tags: scan ? propValues.tags : [],
      concurrent_tasks: scan ? scan.concurrent_tasks : 1,
      useDateRange: !!(
        scan?.arguments?.start_datetime || scan?.arguments?.end_datetime
      ),
      startDate: scan?.arguments?.start_datetime || '',
      endDate: scan?.arguments?.end_datetime || ''
    });

    const [organizationOptions, setOrganizationOptions] =
      useState<OrganizationOption[]>(organizationOption);
    // const [tagOptions, setTagOptions] = useState<OrganizationOption[]>([]);
    const [values, setValues] = useState<ScanFormValues>(setDefault());
    const [schemaUpdated, setSchemaUpdated] = useState<boolean>(false);
    const [dateRangeError, setDateRangeError] = useState<string>('');
    const scanSchemaEntry = scanSchema[values.name];
    const hasSchema = Boolean(scanSchemaEntry);
    const maxConcurrentTasks = hasSchema ? scanSchemaEntry.max_concurrent_tasks : 10;

    const onChange = (name: string, value: any) => {
      setValues((values) => ({
        ...values,
        [name]: value
      }));
    };

    const setDefaultValues = useCallback(() => {
      setOrganizationOptions(organizationOption);
      // setTagOptions(tags.map((tag) => ({ label: tag.name, value: tag.id })));
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
          is_single_scan:
            scan.is_single_scan ||
            !!(scan.arguments?.start_datetime || scan.arguments?.end_datetime),
          organizations: propValues.organizations,
          // tags: propValues.tags,
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
      // propValues.tags,
      // tags,
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
    }, [values.startDate, values.endDate, dateRangeError, values.useDateRange]);

    return (
      <>
        <Box sx={{ mt: 1 }}>
          {type === 'create' && (
            <Autocomplete
              disableClearable
              value={values.name}
              options={Object.keys(scanSchema).sort()}
              size="small"
              fullWidth
              onChange={(_, newValue) => onChange('name', newValue)}
              renderInput={(params) => <TextField {...params} label="Scan Name" />}
            />
          )}
          <Box sx={{ m: 1 }}>
            <FormHelperText sx={{ fontSize: '0.7rem' }}>Scan Description</FormHelperText>
            <Typography variant="caption">
              {scanSchema[values.name]?.description || 'No description available.'}
            </Typography>
          </Box>
          {(values.name === 'censysIpv4' ||
            values.name === 'censysCertificates' ||
            (schemaUpdated && !scanSchema[values.name].global) ||
            !global) && (
              <FormControlLabel
                control={<MuiCheckbox
                  onChange={(e) => onChange('is_granular', e.target.checked)}
                  checked={values.is_granular}
                />}
                label="Limit enabled organizations"
              />

            )}
          {values.is_granular && (
            <Stack spacing={2} my={1}>
              <Autocomplete
                multiple
                size="small"
                options={organizationOptions}
                value={values.organizations}
                getOptionLabel={(option) => option.label}
                isOptionEqualToValue={(option, value) => option.value === value.value}
                onChange={(_, newValue) => onChange('organizations', newValue)}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Enabled Organizations"
                    placeholder="Organizations"
                  />
                )}
              />
              {/* Tag selection is currently unused. This code is retained for potential future restoration. */}
              {/* <Autocomplete
                // value={values.tags}
                options={tagOptions.sort()}
                size="small"
                fullWidth
                isOptionEqualToValue={(option, value) => option.value === value.value}
                renderInput={(params) => <TextField {...params} label="Enabled Organization Tags" />}
              /> */}
            </Stack>
          )}
          {values.name === 'vulnScanningSync' && (
            <Box>
              <FormControlLabel
                control={
                  <MuiCheckbox
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
                }
                label="Limit scan to specific date range"
                sx={{ width: '100%' }}
              />
              {values.useDateRange && (
                <Grid container spacing={1} sx={{ mb: 1 }}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="body1" pb={1}>
                      Start Date (UTC)
                    </Typography>
                    <TextField
                      id="start_datetime"
                      name="start_datetime"
                      size="small"
                      fullWidth
                      type="datetime-local"
                      value={values.startDate}
                      onChange={(e) => onChange('startDate', e.target.value)}
                      slotProps={{
                        htmlInput: {
                          max: getUTCNowString()
                        }
                      }}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Typography variant="body1" pb={1}>
                      End Date and Time
                    </Typography>
                    <TextField
                      id="end_datetime"
                      name="end_datetime"
                      size="small"
                      fullWidth
                      type="datetime-local"
                      value={values.endDate}
                      onChange={(e) => onChange('endDate', e.target.value)}
                      slotProps={{
                        htmlInput: {
                          max: getUTCNowString()
                        }
                      }}
                    />
                  </Grid>
                  <Grid size={{ xs: 12 }}>
                    <Typography variant="caption" color="red">Must run once while limiting to a date range</Typography>
                    {dateRangeError && (
                      <Typography variant="caption" color="red">{dateRangeError}</Typography>
                    )}
                  </Grid>
                </Grid>
              )}
            </Box>
          )}
          <FormControlLabel control={<MuiCheckbox checked={values.is_single_scan}
            disabled={values.useDateRange}
            onChange={(e) => onChange('is_single_scan', e.target.checked)} />} label="Run scan once" sx={{ width: '100%' }} />
          {!values.is_single_scan && (
            <Grid container spacing={2} mb={3}>
              <Grid size={{ xs: 12, sm: 3 }} sx={{ alignSelf: "center" }}>
                <Typography>Run every</Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  size="small"
                  fullWidth
                  sx={{ minWidth: 120 }}
                  id="frequency"
                  name="frequency"
                  type="number"
                  value={values.frequency}
                  onChange={(e) => onChange(e.target.name, Number(e.target.value))}
                  slotProps={{
                    htmlInput: {
                      min: 1
                    },
                  }}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 5 }}>
                <TextField
                  size="small"
                  fullWidth
                  sx={{ minWidth: 120 }}
                  select
                  aria-label="Select frequency unit dropdown"
                  id="frequencyUnit"
                  name="frequencyUnit"
                  onChange={(e) => onChange(e.target.name, e.target.value)}
                  value={values.frequencyUnit}

                >
                  <MenuItem value="hour" key="hour">Hour(s)</MenuItem>
                  <MenuItem value="day" key="day">Day(s)</MenuItem>
                </TextField>
              </Grid>
            </Grid>
          )}
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }} sx={{ alignSelf: "center" }}>
              <Typography sx={{ overflow: 'visible' }}>Number of Concurrent Tasks</Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                size="small"
                fullWidth
                id="concurrent_tasks"
                name="concurrent_tasks"
                type="number"
                value={values.concurrent_tasks}
                onChange={(e) => onChange(e.target.name, Number(e.target.value))}
                slotProps={{
                  htmlInput: {
                    min: 1,
                    ...(maxConcurrentTasks != null && { max: maxConcurrentTasks })
                  },
                }}
              />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <FormHelperText>
                {maxConcurrentTasks != null
                  ? `This scan allows a maximum of ${maxConcurrentTasks} concurrent scans`
                  : 'This scan allows no limit of concurrent tasks'
                }
              </FormHelperText>
            </Grid>
          </Grid>
        </Box>
        <MuiButton onClick={async (e) => {
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
            // tags: values.tags,
            frequency: values.frequency,
            frequencyUnit: values.frequencyUnit,
            is_granular: values.is_granular,
            is_single_scan: values.is_single_scan,
            concurrent_tasks: values.concurrent_tasks
          });
        }}>Submit</MuiButton>
      </>
    );
  };
