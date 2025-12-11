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

// Map display field names to server field names for both sorting and filtering
export const mapDisplayFieldToServerField = (
  field: string | undefined
): string | undefined => {
  if (field === 'is_kev_display') return 'is_kev';
  if (field === 'is_kev_ransomware_display') return 'is_kev_ransomware';
  return field;
};

export const convertStringToBooleanValue = (field: string, value: any): any => {
  if (field === 'is_kev' || field === 'is_kev_ransomware') {
    if (typeof value === 'string') {
      const lowerCaseValue = value.toLowerCase();
      if (lowerCaseValue === 'yes' || lowerCaseValue === 'true') return true;
      if (lowerCaseValue === 'no' || lowerCaseValue === 'false') return false;
      return null;
    }
  }
  return value;
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
      // Map display field names to server field names
      // const serverField = mapDisplayFieldToServerField(cur.field) || cur.field;

      // // Convert string values to boolean values for is_kev_display and is_kev_ransomware_display fields
      // if (serverField === 'is_kev' || serverField === 'is_kev_ransomware') {
      //   acc[serverField] = convertStringToBooleanValue(serverField, cur.value);
      // } else {
      //   acc[serverField] = cur.value as string | boolean | null;
      // }

      if (cur.field === 'is_kev' || cur.field === 'is_kev_ransomware') {
        acc[cur.field] = convertStringToBooleanValue(cur.field, cur.value);
      } else {
        acc[cur.field] = cur.value as string | boolean | null;
      }

      // acc[serverField] = cur.value as string | boolean | null;
      // acc[cur.field] = cur.value as string | boolean | null;
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
