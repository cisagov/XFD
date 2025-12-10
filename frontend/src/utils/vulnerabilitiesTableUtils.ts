import { GridFilterItem } from '@mui/x-data-grid';
import { ORGANIZATION_EXCLUSIONS } from 'hooks/useUserTypeFilters';
import { UserOrganization } from 'types';
import { LocationState } from 'types/vulnerabilities';

const titleCase = (str: string) =>
  str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();

const severityLevels: string[] = [
  'N/A',
  'Low',
  'Medium',
  'High',
  'Critical',
  'Other'
];

export const formatSeverity = (severity?: any) => {
  const titleCaseSev = titleCase(severity);
  if (severityLevels.includes(titleCaseSev)) {
    return titleCaseSev;
  }
  if (
    !titleCaseSev ||
    ['None', 'Null', 'N/a', 'Undefined', 'undefined', ''].includes(titleCaseSev)
  ) {
    return 'N/A';
  } else {
    return 'Other';
  }
};

export const extractInitialFilters = (state: LocationState) => {
  const hiddenFilters: GridFilterItem[] = [];
  if (state?.title) {
    hiddenFilters.push({
      field: 'title',
      value: state.title,
      operator: 'contains'
    });
  }
  if (state?.domain) {
    hiddenFilters.push({
      field: 'domain',
      value: state.domain,
      operator: 'contains'
    });
  }
  if (state?.severity) {
    hiddenFilters.push({
      field: 'severity',
      value: state.severity,
      operator: 'contains'
    });
  }
  if (state?.kev) {
    hiddenFilters.push({
      field: 'is_kev',
      value: state.kev,
      operator: 'equals'
    });
  }
  if (state?.orgId) {
    hiddenFilters.push({
      field: 'organization',
      value: state.orgId,
      operator: 'equals'
    });
  }
  if (state?.startDate) {
    hiddenFilters.push({
      field: 'earliest_date',
      value: state.startDate,
      operator: 'equals'
    });
  }
  if (state?.endDate) {
    hiddenFilters.push({
      field: 'latest_date',
      value: state.endDate,
      operator: 'equals'
    });
  }
  if (state?.dateRange) {
    hiddenFilters.push({
      field: 'date_range',
      value: state.dateRange,
      operator: 'equals'
    });
  }
  if (state?.scanType) {
    hiddenFilters.push({
      field: 'scan_type',
      value: state.scanType,
      operator: 'equals'
    });
  }
  return hiddenFilters;
};

export const normalizeFilters = (
  filters: GridFilterItem[],
  currentOrganization?: UserOrganization | null | undefined,
  userType?: string
) => {
  const result = filters
    .filter((f) => f.value !== undefined && f.value !== null && f.value !== '')
    .reduce<Record<string, string | boolean | null>>((acc, cur) => {
      let field = cur.field;
      let value = cur.value;

      // Handle display field filters - convert field names and values
      if (field === 'is_kev_display') {
        field = 'is_kev';
        if (typeof value === 'string') {
          const v = value.toLowerCase();
          if (v === 'yes' || v === 'true') value = true;
          else if (v === 'no' || v === 'false') value = false;
          else if (v === 'n/a') value = null;
          else value = null;
        } else {
          value = value == null ? null : Boolean(value);
        }
      } else if (field === 'is_kev_ransomware_display') {
        field = 'is_kev_ransomware';
        if (typeof value === 'string') {
          const v = value.toLowerCase();
          if (v === 'yes' || v === 'true') value = true;
          else if (v === 'no' || v === 'false') value = false;
          else if (v === 'n/a') value = null;
          else value = null;
        } else {
          value = value == null ? null : Boolean(value);
        }
      }

      acc[field] = value as string | boolean | null;
      return acc;
    }, {});
  if (
    result['state'] &&
    !['open', 'closed'].includes(result['state'] as string)
  ) {
    const stateValue = result['state'];
    const substate =
      typeof stateValue === 'string'
        ? stateValue.match(/\((.*)\)/)?.[1]
        : undefined;
    if (substate) {
      result['substate'] = substate.toLowerCase().replace(' ', '-');
      delete result['state'];
    }
  }

  const isExcludedOrg = ORGANIZATION_EXCLUSIONS.some((exc) =>
    currentOrganization?.name.toLowerCase().includes(exc)
  );

  if (currentOrganization && !isExcludedOrg && userType === 'standard') {
    result['organization'] = currentOrganization.id;
  }

  if (result['severity']) {
    result['severity'] = formatSeverity(result['severity']);
  }

  return result;
};
