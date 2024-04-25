import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import ContactIcon from './icons/ContactIcon';
import EnrollIcon from './icons/EnrollIcon';

const handleRedirectCSA = () => {
  window.open('https://www.cisa.gov/about/regions', '_blank');
};

const handleRedirectCrossfeed = () => {
  window.open('https://www.cisa.gov/cyber-hygiene-service', '_blank');
};

export const RSCNextSteps: React.FC = () => {
  return (
    <Box
      sx={{
        flexGrow: 1,
        padding: 2,
        backgroundColor: '#F5FAFC',
        borderRadius: 1,
        border: '.1rem solid #B8D9E8'
      }}
    >
      <Stack spacing={2}>
        <Box sx={{ width: 'auto', padding: 1, borderRadius: 2 }}>
          <Typography variant="h5" gutterBottom component="div" color="#005288">
            Next Steps
          </Typography>
        </Box>
        <Box
          sx={{
            width: 'auto',
            bgcolor: 'white',
            padding: 2,
            borderRadius: 2,
            border: '.1rem solid #0078AE'
          }}
        >
          <Stack
            direction="row"
            spacing={2}
            onClick={handleRedirectCSA}
            style={{ cursor: 'pointer' }}
          >
            <ContactIcon />
            <Stack>
              <Typography
                variant="h6"
                gutterBottom
                component="div"
                color="#005288"
              >
                Contact your CSA
              </Typography>
              <Typography variant="body1" gutterBottom component="div">
                CISA&apos;s program of work is carried out across the nation by
                personnel assigned to its 10 regional offices. Your regional
                Cybersecurity Advisor (CSA) is here to support you.
              </Typography>
            </Stack>
          </Stack>
        </Box>
        <Box
          sx={{
            width: 'auto',
            bgcolor: 'white',
            padding: 2,
            borderRadius: 2,
            border: '.1rem solid #0078AE'
          }}
        >
          <Stack
            direction="row"
            spacing={2}
            onClick={handleRedirectCrossfeed}
            style={{ cursor: 'pointer' }}
          >
            <EnrollIcon size={40} />
            <Stack>
              <Typography
                variant="h6"
                gutterBottom
                component="div"
                color="#005288"
              >
                Enroll in Crossfeed
              </Typography>
              <Typography variant="body1" gutterBottom component="div">
                Automatically scan and organize vulnerabilities.
              </Typography>
            </Stack>
          </Stack>
        </Box>
      </Stack>
    </Box>
  );
};
