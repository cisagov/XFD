import React from 'react';
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  Theme
} from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface BreakpointOverrides {
    mds: true;
  }
  interface BreakpointsOptions {
    values: {
      xs: number;
      sm: number;
      mds: number;
      md: number;
      lg: number;
      xl: number;
    };
  }
  interface Palette {
    disabled: Palette['primary'];
    neutrals: Palette['primary'];
  }

  interface PaletteOptions {
    disabled?: PaletteOptions['primary'];
    neutrals?: PaletteOptions['primary'];
  }

  interface PaletteColor {
    darker?: string;
    white?: string;
    black?: string;
  }

  interface SimplePaletteColorOptions {
    darker?: string;
    white?: string;
    black?: string;
  }

  interface TypographyVariants {
    boldBody: React.CSSProperties;
    largeBody: React.CSSProperties;
    subMenuText: React.CSSProperties;
    logText: React.CSSProperties;
    globalNav: React.CSSProperties;
    link: React.CSSProperties;
    miniStatCallout: React.CSSProperties;
    statCallout: React.CSSProperties;
    uiElementsI: React.CSSProperties;
    uiElementsII: React.CSSProperties;
    uiElementsIII: React.CSSProperties;
  }
  interface TypographyVariantsOptions {
    boldBody: React.CSSProperties;
    largeBody: React.CSSProperties;
    subMenuText: React.CSSProperties;
    logText: React.CSSProperties;
    globalNav: React.CSSProperties;
    link: React.CSSProperties;
    miniStatCallout: React.CSSProperties;
    statCallout: React.CSSProperties;
    uiElementsI: React.CSSProperties;
    uiElementsII: React.CSSProperties;
    uiElementsIII: React.CSSProperties;
  }
}

declare module '@mui/material/Button' {
  interface ButtonPropsVariantOverrides {
    globalNav: true;
    primaryContained: true;
  }
}

declare module '@mui/material/Chip' {
  interface ChipPropsVariantOverrides {
    graphOutlinedInactive: true;
    graphOutlinedActive: true;
  }
}

declare module '@mui/material/styles' {
  interface ZIndex {
    FilterDrawerV2: number;
  }
}

declare module '@mui/material/Typography' {
  interface TypographyPropsVariantOverrides {
    boldBody: true;
    largeBody: true;
    subMenuText: true;
    logText: true;
    globalNav: true;
    largeBody: true;
    link: true;
    miniStatCallout: true;
    statCallout: true;
    uiElementsI: true;
    uiElementsII: true;
    uiElementsIII: true;
  }
  interface TypographyPropsColorOverrides {
    disabled: true;
  }
}

const theme = createTheme({
  breakpoints: {
    values: {
      xs: 0,
      sm: 480,
      mds: 750,
      md: 769,
      lg: 1024,
      xl: 1440
    }
  },
  components: {
    MuiButton: {
      variants: [
        {
          props: { variant: 'primaryContained' },
          style: ({ theme }: { theme: Theme }) => ({
            backgroundColor: theme.palette.primary.dark,
            color: theme.palette.neutrals.white,
            '&:hover': {
              backgroundColor: theme.palette.primary.darker
            },
            height: '40px',
            padding: '10px 16px 10px 16px',
            borderRadius: '4px',
            ...theme.typography.button
          })
        },
        {
          props: { variant: 'globalNav' },
          style: ({ theme }) => ({
            ...theme.typography.globalNav,
            textTransform: 'none',
            color: theme.palette.primary.dark,
            backgroundColor: 'transparent',
            borderRadius: 0,
            whiteSpace: 'nowrap',
            '&:hover': {
              color: theme.palette.primary.darker
            }
          })
        }
      ]
    },
    MuiChip: {
      variants: [
        {
          props: {
            variant: 'graphOutlinedInactive'
          },
          style: ({ theme }) => ({
            backgroundColor: theme.palette.neutrals.white,
            color: theme.palette.primary.dark,
            border: `1px solid ${theme.palette.primary.dark}`,

            fontWeight: 'medium',

            '&:hover': {
              backgroundColor: theme.palette.primary.light
            }
          })
        },
        {
          props: {
            variant: 'graphOutlinedActive'
          },
          style: ({ theme }) => ({
            backgroundColor: theme.palette.primary.dark,
            color: theme.palette.neutrals.white,

            fontWeight: 'medium',

            '&:hover': {
              opacity: 0.8
            }
          })
        }
      ]
    },
    // To-do: Re-enable this after clarification with Design Team
    // MuiChip: {
    //   styleOverrides: {
    //     root: {
    //       borderRadius: '4px',
    //       fontSize: '1.167rem',
    //       fontWeight: 'medium',
    //       height: '24px',
    //       padding: '2px 14px 2px 14px',
    //       '&:hover': {
    //         backgroundColor: '#ECF7FF'
    //       }
    //     }
    //   }
    // }
    MuiIconButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          color: theme.palette.primary.dark,
          '&:hover': {
            color: theme.palette.primary.darker
          }
        })
      }
    },
    MuiLink: {
      styleOverrides: {
        root: ({ theme }) => ({
          ...theme.typography.link,
          color: theme.palette.primary.dark,
          '&:hover': {
            color: theme.palette.primary.darker
          }
        })
      }
    },
    MuiMenuItem: {
      styleOverrides: {
        root: ({ theme }) => ({
          color: theme.palette.primary.dark,
          fontSize: '1rem',
          '&:hover': {
            backgroundColor: theme.palette.primary.light,
            color: theme.palette.primary.dark
          },
          '&.Mui-selected': {
            backgroundColor: theme.palette.primary.light,
            color: theme.palette.primary.dark
          }
        })
      }
    },
    MuiListItemText: {
      styleOverrides: {
        primary: ({ theme }) => ({
          fontSize: '1rem',
          color: theme.palette.primary.dark
        })
      }
    },
    MuiListItemButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          '&:hover': {
            backgroundColor: theme.palette.primary.light
          },
          '&.Mui-selected': {
            backgroundColor: theme.palette.primary.light
          }
        })
      }
    }

    // To-do: Re-enable this after clarification with Design Team
    // MuiChip: {
    //   styleOverrides: {
    //     root: {
    //       borderRadius: '4px',
    //       fontSize: '1.167rem',
    //       fontWeight: 500,
    //       height: '24px',
    //       padding: '2px 14px 2px 14px',
    //       '&:hover': {
    //         backgroundColor: '#ECF7FF'
    //       }
    //     }
    //   }
    // }
  },

  palette: {
    primary: {
      main: '#0078AE',
      light: '#ECF7FF',
      dark: '#005288',
      darker: '#002B45'
    },
    secondary: {
      main: '#EC7633',
      light: '#FFB38A',
      dark: '#C33200',
      darker: '#731A00'
    },
    error: {
      main: '#C41230'
    },
    success: {
      main: '#5E9732'
    },
    background: {
      default: '#FFFFFF'
    },
    disabled: {
      main: '#BDBDBD', // Set your desired disabled color here
      contrastText: '#FFFFFF' // Optional: define text color for the disabled state
    },
    neutrals: {
      main: '#646566',
      light: '#A9AEB1',
      dark: '#2F2F30',
      white: '#FFFFFF',
      black: '#000000'
    }
  },
  typography: {
    fontFamily: 'source sans pro, sans-serif',
    body1: {
      fontSize: '14px',
      fontWeight: 500,
      textTransform: 'none'
    },
    boldBody: {
      fontSize: '14px',
      fontWeight: 'bold',
      textTransform: 'none'
    },
    largeBody: {
      fontSize: '16px',
      fontWeight: 400,
      textTransform: 'none',
      letterSpacing: '0%',
      lineHeight: '22px'
    },
    logText: {
      fontSize: '18px',
      fontWeight: 400,
      textTransform: 'none',
      letterSpacing: '0%',
      lineHeight: '22px'
    },
    subMenuText: {
      fontSize: '16px',
      fontWeight: 600,
      textTransform: 'none'
    },
    button: {
      fontSize: '14px',
      fontWeight: 'bold',
      textTransform: 'uppercase'
    },
    globalNav: {
      fontSize: '16px',
      fontWeight: 'bold',
      textTransform: 'none'
    },
    h1: {
      fontSize: '36px',
      fontWeight: 'bold',
      textTransform: 'none'
    },
    h2: {
      fontSize: '24px',
      fontWeight: 600,
      textTransform: 'none'
    },
    h3: {
      fontSize: '18px',
      fontWeight: 600,
      textTransform: 'none'
    },
    link: {
      fontSize: '14px',
      fontWeight: 500,
      textDecoration: 'underline'
    },
    miniStatCallout: {
      fontSize: '20px',
      fontWeight: 500,
      textTransform: 'uppercase'
    },
    statCallout: {
      fontSize: '36px',
      fontWeight: 'bold',
      textTransform: 'uppercase'
    },
    uiElementsI: {
      fontSize: '10px',
      fontWeight: 400,
      textTransform: 'none'
    },
    uiElementsII: {
      fontSize: '12px',
      fontWeight: 500,
      textTransform: 'none'
    },
    uiElementsIII: {
      fontSize: '12px',
      fontWeight: 500,
      fontStyle: 'italic',
      textTransform: 'none'
    }
  },
  zIndex: {
    FilterDrawerV2: 1201
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
