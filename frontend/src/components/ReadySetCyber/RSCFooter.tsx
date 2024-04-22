import React from 'react';
import { Box, Grid, Link, Typography, Stack } from '@mui/material';
import cisaFooterLogo from './assets/cisa_footer_logo.png';
import { links } from './links';

export const RSCFooter: React.FC = () => {
  return (
    <Box
      sx={{
        width: '100%',
        display: 'flex',
        position: 'relative',
        bottom: 0,
        justifyContent: 'center',
        backgroundColor: '#005285',
        paddingTop: '1em',
        paddingBottom: '1em'
      }}
    >
      <Box
        sx={{
          maxWidth: '80vw',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}
      >
        <Stack direction={'row'} gap={'1em'} paddingBottom={'2em'}>
          <img
            src={cisaFooterLogo}
            alt="CISA Footer Logo"
            style={{
              width: 55,
              height: 55,
              flexShrink: 0
            }}
          />
          <Stack justifyContent={'center'}>
            <Typography
              style={{
                color: 'white',
                fontSize: '0.85em'
              }}
            >
              CISA.gov
            </Typography>
            <Typography
              style={{
                color: 'white',
                fontSize: '0.85em'
              }}
            >
              An Official website of the U.S. Department of Homeland Security
            </Typography>
          </Stack>
        </Stack>
        <Grid
          container
          spacing={2}
          sx={{
            textAlign: {
              xs: 'center',
              sm: 'left'
            }
          }}
        >
          {links.map((link, index) => (
            <Grid item xs={4} sm={3} key={index}>
              <Link
                style={{
                  color: 'white',
                  textDecoration: 'underline',
                  fontSize: '0.9em'
                }}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                {link.text}
              </Link>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
};
