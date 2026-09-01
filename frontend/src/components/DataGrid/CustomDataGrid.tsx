import React from 'react';
import GlobalStyles from '@mui/material/GlobalStyles';

// DataGrid Components
import { DataGrid } from '@mui/x-data-grid';
import type { DataGridProps, GridValidRowModel } from '@mui/x-data-grid';

// Types
import type { Theme } from '@mui/material/styles';

// Provides a wrapper around the MUI DataGrid component to ensure that the z-index of the DataGrid and its child components are always set to one less than the appBar z-index, regardless of the theme configuration.
// This is important for ensuring that the filter panel and menu buttons do not overlap with other UI elements like the appBar.

type PanelSlotProps = {
  sx?:
    | Record<string, unknown>
    | Array<Record<string, unknown>>
    | ((theme: Theme) => Record<string, unknown>);
};

type BasePopperSlotProps = {
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
  const basePopperSlotProps = slotProps?.basePopper as
    | BasePopperSlotProps
    | undefined;
  const consumerBasePopperSx = basePopperSlotProps?.sx;

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

  // Ensures that the z-index of the base popper (used for dropdowns) is always set to one less than the appBar z-index, regardless of the theme configuration.

  const mergedBasePopperSx = (theme: Theme) => {
    const baseSx = {
      zIndex: theme.zIndex.appBar - 1
    };

    if (!consumerBasePopperSx) {
      return baseSx;
    }

    if (typeof consumerBasePopperSx === 'function') {
      return {
        ...baseSx,
        ...consumerBasePopperSx(theme)
      };
    }

    if (Array.isArray(consumerBasePopperSx)) {
      return Object.assign({}, baseSx, ...consumerBasePopperSx);
    }

    return {
      ...baseSx,
      ...consumerBasePopperSx
    };
  };

  const mergedSlotProps = {
    ...slotProps,
    basePopper: {
      ...(basePopperSlotProps ?? {}),
      sx: mergedBasePopperSx
    },
    panel: {
      ...(panelSlotProps ?? {}),
      sx: mergedPanelSx
    }
  };

  return (
    <>
      {/* GlobalStyles is used to ensure that the z-index of the filter panel and its paper component is always set to one less than the appBar z-index, regardless of the theme configuration. */}
      {/* serves as a fallback to ensure that the z-index is correct even if the slotProps are not provided or are overridden by the consumer of the AppDataGrid component. */}
      <GlobalStyles
        styles={(theme: Theme) => ({
          '.MuiDataGrid-menu, .MuiDataGrid-panel': {
            zIndex: `${theme.zIndex.appBar - 1} !important`
          },
          '.MuiDataGrid-menu .MuiPaper-root, .MuiDataGrid-panel .MuiPaper-root':
            {
              zIndex: `${theme.zIndex.appBar - 1} !important`
            }
        })}
      />
      <DataGrid
        {...rest}
        slotProps={mergedSlotProps as DataGridProps<R>['slotProps']}
      />
    </>
  );
};

export default AppDataGrid;
