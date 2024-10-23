import React, { useMemo } from 'react';
import { classes, Root } from './Styling/filterTagsStyle';
import { ContextType } from '../../context/SearchProvider';
import { Chip } from '@mui/material';
import { REGIONAL_ADMIN, useUserLevel } from 'hooks/useUserLevel';
import { STANDARD_USER } from 'context/userStateUtils';
import { REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS } from 'hooks/useUserTypeFilters';

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
  'organization.regionId': {
    labelAccessor: (t) => {
      return 'Region';
    },
    filterValueAccssor: (t) => {
      return t;
    },
    trimAfter: 10
  },
  'vulnerabilities.severity': {
    labelAccessor: (t) => {
      return 'Severity';
    },
    filterValueAccssor(t) {
      return t;
    }
  },
  ip: {
    labelAccessor: (t) => {
      return 'IP';
    },
    filterValueAccssor(t) {
      return t;
    }
  },
  name: {
    labelAccessor: (t) => {
      return 'Name';
    },
    filterValueAccssor(t) {
      return t;
    }
  },
  fromRootDomain: {
    labelAccessor: (t) => {
      return 'Root Domain(s)';
    },
    filterValueAccssor(t) {
      return t;
    }
  },
  organizationId: {
    labelAccessor: (t) => {
      return 'Organization';
    },
    filterValueAccssor: (t) => {
      return t.name;
    },
    trimAfter: 2
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
    filterValueAccssor(t) {
      return t;
    },
    trimAfter: 6
  },
  'vulnerabilities.cve': {
    labelAccessor: (t) => {
      return 'CVE';
    },
    filterValueAccssor(t) {
      return t;
    },
    trimAfter: 3
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

export const FilterTags: React.FC<Props> = ({ filters, removeFilter }) => {
  const { userLevel } = useUserLevel();

  const disabledFilters = useMemo(() => {
    if (userLevel === STANDARD_USER) {
      return ['Region', 'Organization'];
    }
    if (userLevel === REGIONAL_ADMIN) {
      return REGIONAL_USER_CAN_SEARCH_OTHER_REGIONS ? [] : ['Region'];
    }
  }, [userLevel]);

  const filtersByColumn: FlatFilters = useMemo(() => {
    return filters.reduce((acc, nextFilter) => {
      const fieldAccessors = FIELD_TO_LABEL_MAP[nextFilter.field] ?? null;
      const value = fieldAccessors
        ? ellipsisPastIndex(
            nextFilter.values.map((item: any) =>
              fieldAccessors.filterValueAccssor(item)
            ),
            fieldAccessors.trimAfter ? fieldAccessors.trimAfter - 1 : null
          ).join(', ')
        : nextFilter.values.join(', ');
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
  }, [filters]);

  return (
    <Root>
      {filtersByColumn.map((filter, idx) => (
        <Chip
          key={idx}
          disabled={disabledFilters?.includes(filter.label)}
          color={'primary'}
          classes={{ root: classes.chip }}
          label={
            <>
              <strong>{filter.label}:</strong> {filter.value}
            </>
          }
          onDelete={() => {
            if (filter.onClear) {
              console.log('custom clear');
              filter.onClear();
              return;
            }
            filter.values.forEach((val) => {
              removeFilter(filter.field, val, filter.type);
            });
          }}
        />
      ))}
    </Root>
  );
};
