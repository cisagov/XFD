import React from 'react';
import {
  createTheme,
  ThemeProvider,
  Theme,
  StyledEngineProvider,
  responsiveFontSizes, 
  
} from '@mui/material/styles';
import { TypographyOptions } from '@mui/material/styles/createTypography';
import { fontSize, ThemeOptions } from '@mui/system';

declare module '@mui/material/styles' {
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  interface DefaultTheme extends Theme {
  }
  interface TypographyVariants { 
    testVariant: React.CSSProperties
  }
}

interface ExtendedTypographyOptions extends TypographyOptions {
  testVariant: React.CSSProperties
}

declare module '@mui/material/typography' {
  interface TypographyPropsVariantOverrides {
    // Required to allow override of the rendered tag
    testVariant: true
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
  },
  typography:{
    testVariant: {
      fontSize: '1.2rem'
    }
  } as ExtendedTypographyOptions,
  components: {
    MuiTypography: {
      defaultProps: {
        variantMapping: {
          testVariant: 'h1'
        }
      }
     }
  } 
});

theme.typography.testVariant = {
  fontSize: '1.2rem',
  [theme.breakpoints.up('md')]: {
    fontSize: '2.4rem',
  },
  
}


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
