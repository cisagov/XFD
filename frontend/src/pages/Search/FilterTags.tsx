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
  };
}

const FIELD_TO_LABEL_MAP: FieldToLabelMap = {
  'organization.regionId': {
    labelAccessor: (t) => {
      return 'Region';
    },
    filterValueAccssor: (t) => {
      return t;
    }
  },
  organizationId: {
    labelAccessor: (t) => {
      return 'Organization';
    },
    filterValueAccssor: (t) => {
      return t.name;
    }
  },
  'services.port': {
    labelAccessor: (t) => {
      return 'Port';
    },
    filterValueAccssor(t) {
      return t;
    }
  },
  'vulnerabilities.cve': {
    labelAccessor: (t) => {
      return 'CVE';
    },
    filterValueAccssor(t) {
      return t;
    }
  }
};

type FlatFilters = {
  field: string;
  label: string;
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
        ? nextFilter.values
            .map((item: any) => fieldAccessors.filterValueAccssor(item))
            .join(', ')
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
    <Root
      sx={{
        marginTop: 1
      }}
    >
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
            filter.values.forEach((val) => {
              removeFilter(filter.field, val, filter.type);
            });
          }}
        />
      ))}
    </Root>
  );
};
