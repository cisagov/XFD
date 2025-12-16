import { GridFilterItem, GridFilterModel } from '@mui/x-data-grid';
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
  userType?: string,
  orgId?: string
) => {
  const result = filters
    .filter((f) => {
      if (f.value === undefined || f.value === null) return false;
      if (typeof f.value === 'string' && f.value.trim() === '') return false;
      return true;
    })
    .reduce<Record<string, string | boolean | null>>((acc, cur) => {
      acc[cur.field] = convertStringToBooleanValue(cur.field, cur.value);

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

  if (orgId) {
    result['organization'] = orgId;
  }

  return result;
};

export const shouldTriggerFilterUpdate = (
  modelItems: GridFilterItem[],
  lastFilterValuesKey: string
): { shouldUpdate: boolean; newKey: string } => {
  // Extract filters with actual values
  const filtersWithValues = modelItems
    .filter(
      (item) =>
        item.value !== undefined && item.value !== null && item.value !== ''
    )
    .map((f) => ({
      field: f.field,
      operator: f.operator,
      value: f.value
    }))
    .sort((a, b) => a.field.localeCompare(b.field));

  const valuesKey = JSON.stringify(filtersWithValues);
  const hadFilters = lastFilterValuesKey !== '[]';
  const hasFilters = filtersWithValues.length > 0;

  // No change - skip update
  if (valuesKey === lastFilterValuesKey) {
    return { shouldUpdate: false, newKey: lastFilterValuesKey };
  }

  // Intermediate state: had filters, now have none, but items exist with undefined values
  // This happens when changing filter fields - skip to avoid unnecessary API calls
  if (hadFilters && !hasFilters && modelItems.length > 0) {
    return { shouldUpdate: false, newKey: lastFilterValuesKey };
  }

  // Values actually changed - trigger update
  return { shouldUpdate: true, newKey: valuesKey };
};

export const cleanFilterModelItems = (
  newModel: GridFilterModel,
  previousModel: GridFilterModel
): GridFilterModel => {
  const cleanedItems = newModel.items.map((item, index) => {
    const prevItem = previousModel.items[index];

    // Clear value when field changes (prevents value carryover)
    if (prevItem && prevItem.field !== item.field && prevItem.id === item.id) {
      return { ...item, value: undefined };
    }

    // Normalize empty/null/whitespace values to undefined
    if (
      item.value === '' ||
      item.value === null ||
      (typeof item.value === 'string' && item.value.trim() === '')
    ) {
      return { ...item, value: undefined };
    }

    return item;
  });

  return { ...newModel, items: cleanedItems };
};
