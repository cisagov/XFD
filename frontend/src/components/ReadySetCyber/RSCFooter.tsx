import React from 'react';
import { 
  Box,
  BottomNavigation,
  BottomNavigationAction,
  Grid,
  Link,
  Menu,
  MenuItem,
  Typography,
  Stack, 
} from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import AccountCircleIcon from '@mui/icons-material/AccountCircle'; // Import the AccountCircle icon
import cisaFooterLogo from './assets/cisa_footer_logo.png'; // Import the logo
import { links } from './links';

export const RSCFooter: React.FC = () => {
  const [value, setValue] = React.useState(0);
  const [anchorElement, setAnchorElement] = React.useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElement(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorElement(null);
  };

  return (
    <Box 
      sx={{ 
        width: '100%', 
        position: 'fixed', 
        bottom: 0, height: '20vh', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
      }}
    >
      <BottomNavigation
        value={value}
        onChange={(event, newValue) => {
          setValue(newValue);
        }}
        showLabels
        sx={{ 
          width: '100%',
          height: '20vh', 
          backgroundColor: '#005285'
        }}
      >
        <Grid container direction="column" alignItems="flex-start">
         <Stack>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'flex-start', 
            paddingLeft: '4em', 
            paddingTop: '1.5em' 
            }}
            >
            <Box sx={{ marginRight: '0.7em' }}>
              <img src={cisaFooterLogo} 
                alt="CISA Footer Logo"
                style={{
                  width: 55,
                  height: 55, 
                  flexShrink: 0,
                }}
              /> 
            </Box>
            <Box sx={{paddingTop: '0.2em'}}>
            <Typography style={{ 
              color: 'white',
              fontSize: '0.85em', 
              }}>
              CISA.gov
              </Typography>
            <Typography style={{ 
              color: 'white',
              fontSize: '0.85em', 
              }}>
              An Official website of the U.S. Department of Homeland Security
              </Typography>
             </Box>
          </Box>
            <Box sx={{ paddingLeft: '4em' }}>
              <Grid container spacing={2}>
                {links.map((link, index) => (
                  <Grid item xs={3} key={index}>
                    <Link 
                      style={{ 
                        color: 'white',
                        textDecoration: 'underline',
                        fontSize: '0.9em',
                      }}
                      href={link.href}
                    >
                      {link.text}
                    </Link>
                  </Grid>
                ))}
              </Grid>
            </Box>
          </Stack>
        </Grid>
      </BottomNavigation>
    </Box>
  );
};