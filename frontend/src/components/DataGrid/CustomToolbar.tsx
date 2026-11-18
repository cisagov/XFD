import * as React from 'react';
import type { ReactNode } from 'react';
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
  GridToolbarExport,
  GridToolbarDensitySelector
} from '@mui/x-data-grid';
import Badge from '@mui/material/Badge';

export interface CustomToolbarProps {
  children?: ReactNode;
  disableExport?: boolean;
  exportTitle?: string;
  hasActiveFilters?: boolean;
}

export default function CustomToolbar(props: CustomToolbarProps) {
  const { hasActiveFilters } = props;

  return (
    <GridToolbarContainer
      sx={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        minHeight: 48,
        overflow: 'visible',
        paddingTop: 1.5,
        paddingBottom: 1
      }}
    >
      <GridToolbarColumnsButton />
      <Badge
        color="primary"
        badgeContent={hasActiveFilters ? 1 : 0}
        sx={{
          overflow: 'visible',
          '& .MuiBadge-badge': {
            minWidth: 18,
            height: 18,
            padding: '0 5px',
            top: 4,
            right: 4
          },
          '& .MuiButton-root .MuiBadge-badge': {
            display: 'none' // Hide the button's internal badge
          }
        }}
      >
        <GridToolbarFilterButton />
      </Badge>
      <GridToolbarDensitySelector />
      {props?.disableExport ? (
        <></>
      ) : (
        <GridToolbarExport
          csvOptions={{
            fileName: 'CyHy Dashboard ' + props.exportTitle
          }}
          printOptions={{ disableToolbarButton: true }}
        />
      )}
      {props.children}
    </GridToolbarContainer>
  );
}
