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
  return hiddenFilters;
};

export const normalizeFilters = (
  filters: GridFilterItem[],
  currentOrganization?: UserOrganization | null | undefined,
  userType?: string,
  orgId?: string
) => {
  const result = filters
    .filter((f) => Boolean(f.value))
    .reduce<Record<string, string | boolean>>((acc, cur) => {
      acc[cur.field] = cur.value as string;
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

  if (result['is_kev']) {
    result['is_kev'] = 'true';
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
