import React from 'react';
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider
} from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    disabled: Palette['primary'];
  }

  interface PaletteOptions {
    disabled?: PaletteOptions['primary'];
  }
}

const theme = createTheme({
  palette: {
    primary: {
      main: '#07648D'
    },
    secondary: {
      main: '#28A0CB'
    },
    background: {
      default: '#EFF1F5'
    },
    disabled: {
      main: '#BDBDBD', // Set your desired disabled color here
      contrastText: '#FFFFFF' // Optional: define text color for the disabled state
    }
  },
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 960,
      lg: 1330,
      xl: 1920
    }
  }
});

interface CFThemeProviderProps {
  children: React.ReactNode;
}
export const CFThemeProvider: React.FC<CFThemeProviderProps> = ({
  children
}) => {
  return (
    <StyledEngineProvider injectFirst>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </StyledEngineProvider>
  );
};
