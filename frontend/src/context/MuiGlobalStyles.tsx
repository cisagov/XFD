import React from 'react';
import GlobalStyles from '@mui/material/GlobalStyles';

/**
 * Global overrides for MUI DataGrid popper content (columns panel).
 * Keeps these overrides in one place so App.tsx stays clean.
 */
export const MuiGlobalStyles: React.FC = () => (
  <GlobalStyles
    styles={{
      /* hide the columns panel header / search input rendered in a portal */
      '.MuiDataGrid-columnsManagementHeader, .MuiDataGrid-columnsPanelHeader': {
        display: 'none !important'
      },
      /* additional selector in case different class names appear */
      '.MuiDataGrid-columnsPanel input, .MuiDataGrid-columnsPanel .MuiInputBase-root':
        {
          display: 'none !important'
        }
    }}
  />
);

export default MuiGlobalStyles;
