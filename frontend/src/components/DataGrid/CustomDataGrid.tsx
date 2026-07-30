import React from 'react';

// DataGrid Components
import { DataGrid } from '@mui/x-data-grid';
import type { DataGridProps, GridValidRowModel } from '@mui/x-data-grid';

// Types
import type { Theme } from '@mui/material/styles';

// Provides a wrapper around the MUI DataGrid component to ensure that the z-index of the filter panel is always set to one less than the appBar z-index, regardless of the theme configuration.
// This is important for ensuring that the filter panel does not overlap with other UI elements like the appBar.

type PanelSlotProps = {
  sx?:
    | Record<string, unknown>
    | Array<Record<string, unknown>>
    | ((theme: Theme) => Record<string, unknown>);
};

export const AppDataGrid = <R extends GridValidRowModel>(
  props: DataGridProps<R>
) => {
  const { slotProps, ...rest } = props;

  const panelSlotProps = slotProps?.panel as PanelSlotProps | undefined;
  const consumerPanelSx = panelSlotProps?.sx;

  // Ensures that the z-index of the filter panel is always set to one less than the appBar z-index, regardless of the theme configuration.

  const mergedPanelSx = (theme: Theme) => {
    const baseSx = {
      zIndex: theme.zIndex.appBar - 1
    };

    if (!consumerPanelSx) {
      return baseSx;
    }

    if (typeof consumerPanelSx === 'function') {
      return {
        ...baseSx,
        ...consumerPanelSx(theme)
      };
    }

    if (Array.isArray(consumerPanelSx)) {
      return Object.assign({}, baseSx, ...consumerPanelSx);
    }

    return {
      ...baseSx,
      ...consumerPanelSx
    };
  };

  const mergedSlotProps = {
    ...slotProps,
    panel: {
      ...(panelSlotProps ?? {}),
      sx: mergedPanelSx
    }
  };

  return (
    <DataGrid
      {...rest}
      slotProps={mergedSlotProps as DataGridProps<R>['slotProps']}
    />
  );
};

export default AppDataGrid;
