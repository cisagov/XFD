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
} from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import AccountCircleIcon from '@mui/icons-material/AccountCircle'; // Import the AccountCircle icon
import cisaFooterLogo from './assets/cisa_footer_logo.png'; // Import the logo

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
          <Box sx={{ display: 'flex', alignItems: 'center', paddingLeft: '4em', paddingTop: '1.5em' }}>
            <Box sx={{ marginRight: '1em' }}>
              <img src={cisaFooterLogo} 
                alt="CISA Footer Logo"
                style={{
                  width: 55,
                  height: 55, 
                  flexShrink: 0,
                }}
              /> {/* Use the logo */}
            </Box>
            <Box>
            <Typography variant="h7" style={{ color: 'white' }}>{`CISA.gov\nAn Official website of the U.S. Department of Homeland Security`}</Typography>
            {/* <Typography variant="h6" style={{ color: 'white' }}>CISA.gov</Typography> */}
            </Box>
          </Box>
          <Box sx={{ marginTop: '1em' }}>
            <Grid container spacing={2}>
              {Array.from({ length: 12 }).map((_, index) => (
                <Grid item xs={4} key={index}>
                  <Link 
                    style={{ 
                      color: 'white',
                      textDecoration: 'underline',
                      fontSize: 10,
                     }}
                    href={`#link${index + 1}`} 
                    >
                    Link {index + 1}
                  </Link>
                </Grid>
              ))}
            </Grid>
          </Box>
        </Grid>
      </BottomNavigation>
    </Box>
  );
};