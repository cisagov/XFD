import * as React from 'react';
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
  GridToolbarExport,
  GridToolbarDensitySelector
} from '@mui/x-data-grid';
import Badge from '@mui/material/Badge';

export default function CustomToolbar(props: any) {
  const { hasActiveFilters } = props;
  return (
    <GridToolbarContainer
      sx={{ justifyContent: 'flex-start', paddingTop: 1.5 }}
    >
      <GridToolbarColumnsButton />
      <Badge
        color="primary"
        badgeContent={hasActiveFilters ? 1 : 0}
        sx={{
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
