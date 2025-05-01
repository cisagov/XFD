import React, { useMemo } from 'react';
import { classes, Root } from './Styling/filterTagsStyle';
import { ContextType } from '../../context/SearchProvider';
import { Chip, IconButton } from '@mui/material';
import { FilterAlt } from '@mui/icons-material';
import { REGIONAL_ADMIN, useUserLevel } from 'hooks/useUserLevel';
import { STANDARD_USER } from 'context/userStateUtils';
import { REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS } from 'hooks/useUserTypeFilters';
import { useLocation } from 'react-router-dom';
import { useFilterDrawerContext } from 'context/FilterDrawerContext';

interface Props {
  filters: ContextType['filters'];
  removeFilter: ContextType['removeFilter'];
}

interface FieldToLabelMap {
  [key: string]: {
    labelAccessor: (t: any) => any;
    filterValueAccssor: (t: any) => any;
    trimAfter?: number;
  };
}

type EllipsisPastIndex<T> = (source: T[], index: number | null) => T[];

const ellipsisPastIndex: EllipsisPastIndex<string> = (source, index) => {
  const DEFAULT_INDEX = 3;
  if (index === null || index === 0) {
    return source.slice(0, DEFAULT_INDEX);
  } else if (source.length > index + 1) {
    const remainder = source.length - index - 1;
    return [...source.slice(0, index + 1), `...+${remainder}`];
  } else {
    return source;
  }
};

const FIELD_TO_LABEL_MAP: FieldToLabelMap = {
  'organization.region_id': {
    labelAccessor: (t) => {
      return 'Region';
    },
    filterValueAccssor: (t) => {
      if (Array.isArray(t)) {
        return t.sort((a: string, b: string) => {
          const numA = parseInt(a, 10);
          const numB = parseInt(b, 10);
          return numA - numB;
        });
      }
      return t;
    },
    trimAfter: 10
  },
  'vulnerabilities.severity': {
    labelAccessor: (t) => {
      return 'Severity';
    },
    filterValueAccssor(t) {
      const severityLevels = [
        'N/A',
        'Low',
        'Medium',
        'High',
        'Critical',
        'Other'
      ];
      if (Array.isArray(t)) {
        return t.sort((a: string, b: string) => {
          const aValue = severityLevels.indexOf(a);
          const bValue = severityLevels.indexOf(b);
          return aValue - bValue;
        });
      }
      return t;
    },
    trimAfter: 3
  },
  ip: {
    labelAccessor: (t) => {
      return 'IP';
    },
    filterValueAccssor(t) {
      if (Array.isArray(t)) {
        return t.sort((a: string, b: string) => {
          return a.localeCompare(b);
        });
      }
      return t;
    }
  },
  name: {
    labelAccessor: (t) => {
      return 'Name';
    },
    filterValueAccssor(t) {
      if (Array.isArray(t)) {
        return t.sort((a: string, b: string) => {
          return a.localeCompare(b);
        });
      }
      return t;
    }
  },
  from_root_domain: {
    labelAccessor: (t) => {
      return 'Root Domain(s)';
    },
    filterValueAccssor(t) {
      if (Array.isArray(t)) {
        return t.sort((a: string, b: string) => {
          return a.localeCompare(b);
        });
      }
      return t;
    }
  },
  organization_id: {
    labelAccessor: (t) => {
      return 'Organization';
    },
    filterValueAccssor: (t) => {
      if (Array.isArray(t)) {
        return t
          .map((org) => org.name)
          .sort((a: string, b: string) => {
            return a.localeCompare(b);
          });
      }
      return t.name;
    },
    trimAfter: 3
  },

  query: {
    labelAccessor: (t) => {
      return 'Query';
    },
    filterValueAccssor(t) {
      return t;
    }
  },
  'services.port': {
    labelAccessor: (t) => {
      return 'Port';
    },
    filterValueAccssor: (t) => {
      if (Array.isArray(t)) {
        return t.sort((a: number, b: number) => {
          return a - b;
        });
      }
      return t;
    },
    trimAfter: 6
  },
  'vulnerabilities.cve': {
    labelAccessor: (t) => {
      return 'CVE';
    },
    filterValueAccssor(t) {
      if (Array.isArray(t)) {
        return t.sort((a: string, b: string) => {
          return a.localeCompare(b);
        });
      }
      return t;
    },
    trimAfter: 10
  }
};

type FlatFilters = {
  field: string;
  label: string;
  onClear?: () => void;
  value: any;
  values: any[];
  type: 'all' | 'none' | 'any';
}[];

const filterOrder = [
  'Region',
  'Organization',
  'IP',
  'Name',
  'Root Domain(s)',
  'Port',
  'CVE',
  'Severity'
];

const sortFiltersByOrder = (filters: FlatFilters) => {
  return filters.sort((a, b) => {
    return filterOrder.indexOf(a.label) - filterOrder.indexOf(b.label);
  });
};

export const FilterTags: React.FC<Props> = ({ filters, removeFilter }) => {
  const { pathname } = useLocation();

  const { userLevel } = useUserLevel();
  const { setIsFilterDrawerOpen, isFilterDrawerOpen } =
    useFilterDrawerContext();

  const disabledFilters = useMemo(() => {
    if (userLevel === STANDARD_USER) {
      return ['Region', 'Organization'];
    }
    if (userLevel === REGIONAL_ADMIN) {
      return REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS ? [] : ['Region'];
    }
  }, [userLevel]);

  const filtersByColumn: FlatFilters = useMemo(() => {
    const processedFilters = filters.reduce((acc, nextFilter) => {
      const fieldAccessors = FIELD_TO_LABEL_MAP[nextFilter.field] ?? null;
      const sortedValues = fieldAccessors
        ? fieldAccessors.filterValueAccssor(nextFilter.values)
        : nextFilter.values;
      const value = fieldAccessors
        ? ellipsisPastIndex(
            sortedValues,
            fieldAccessors.trimAfter ? fieldAccessors.trimAfter - 1 : null
          ).join(', ')
        : sortedValues.join(', ');
      const label = fieldAccessors
        ? fieldAccessors.labelAccessor(nextFilter)
        : nextFilter.field.split('.').pop();
      return [
        ...acc,
        {
          ...nextFilter,
          value: value,
          label: label
        }
      ];
    }, []);
    return sortFiltersByOrder(processedFilters);
  }, [filters]);

  return (
    <Root aria-live="polite" aria-atomic="true">
      <IconButton
        aria-label="filter-drawer-toggle"
        sx={{ mt: '0.5rem' }}
        onClick={() => setIsFilterDrawerOpen(!isFilterDrawerOpen)}
      >
        <FilterAlt />
      </IconButton>
      {filtersByColumn.length === 0 && pathname === '/inventory' ? (
        <Chip
          color="primary"
          classes={{ root: classes.chip }}
          label="No Filter(s) Applied"
        />
      ) : (
        filtersByColumn.map((filter, idx) => (
          <Chip
            key={idx}
            disabled={disabledFilters?.includes(filter.label)}
            color="primary"
            classes={{ root: classes.chip }}
            label={`${filter.label}: ${filter.value}`}
            onDelete={
              !disabledFilters?.includes(filter.label)
                ? () => {
                    filter.onClear
                      ? filter.onClear()
                      : filter.values.forEach((val) =>
                          removeFilter(filter.field, val, filter.type)
                        );
                  }
                : undefined
            }
          />
        ))
      )}
    </Root>
  );
};
