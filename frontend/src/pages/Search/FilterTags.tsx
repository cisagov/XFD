import React, { useMemo } from 'react';
import { classes, Root } from './Styling/filterTagsStyle';
import { ContextType } from '../../context/SearchProvider';
import { Chip } from '@mui/material';

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
  }
};

type FlatFilters = {
  field: string;
  label: string;
  value: any;
  values: any[];
  type: 'all' | 'none' | 'any';
}[];

export const FilterTags: React.FC<Props> = (props) => {
  const { filters, removeFilter } = props;

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
          color="primary"
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
