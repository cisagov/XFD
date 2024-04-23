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
        flexDirection: {
          xs: 'column',
          sm: 'row'
        },
        position: 'relative',
        bottom: 0,
        justifyContent: 'center',
        alignItems: {
          xs: 'center', // center horizontally on small screens
          sm: 'initial' // reset to default on larger screens
        },
        backgroundColor: '#005288',
        padding: '1em'
      }}
    >
      <Box
        sx={{
          maxWidth: '80vw',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          paddingBottom: '2em'
        }}
      >
        <Stack
          direction={{ sm: 'column', md: 'row' }}
          gap={{ sm: '-2em', md: '1em' }}
          paddingBottom={'2em'}
        >
          <Link
            href="https://www.cisa.gov/"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img
              src={cisaFooterLogo}
              alt="CISA Footer Logo"
              style={{
                width: 55,
                height: 55,
                flexShrink: 0
              }}
            />
          </Link>
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
              An official website of the U.S. Department of Homeland Security
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
      <Box
        sx={{
          textAlign: {
            xs: 'center',
            sm: 'right'
          },
          alignContent: {
            xs: 'flex-end',
            sm: 'center'
          },
          marginTop: {
            xs: '1em',
            sm: '2em',
            md: '0em'
          }
        }}
      >
        <iframe
          src="https://www.dhs.gov/ntas/"
          name="National Terrorism Advisory System"
          title="National Terrorism Advisory System"
          width="170"
          height="180"
          scrolling="no"
          frameBorder="0"
          style={{ border: 0 }}
        />
      </Box>
    </Box>
  );
};
