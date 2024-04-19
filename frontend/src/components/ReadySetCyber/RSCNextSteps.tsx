import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import ContactSupportOutlinedIcon from '@mui/icons-material/ContactSupportOutlined';
import OutboundOutlinedIcon from '@mui/icons-material/OutboundOutlined';

export const RSCNextSteps: React.FC = () => {
  return (
    <Box
      sx={{
        flexGrow: 1,
        padding: 2,
        backgroundColor: '#dce7fa',
        borderRadius: 1
      }}
    >
      <Stack spacing={2}>
        <Box sx={{ width: 'auto', padding: 1, borderRadius: 2 }}>
          <Typography variant="h5" gutterBottom component="div">
            Next Steps
          </Typography>
        </Box>
        <Box
          sx={{ width: 'auto', bgcolor: 'white', padding: 2, borderRadius: 2 }}
        >
          <Stack direction="row" alignItems="center" spacing={2}>
            <ContactSupportOutlinedIcon fontSize="large" />
            <Stack>
              <Typography variant="h6" gutterBottom component="div">
                Contact your CSA
              </Typography>
              <Typography variant="body1" gutterBottom component="div">
                CISA's program of work is carried out across the nation by
                personnel assigned to its 10 regional offices. Your regional
                Cybersecurity Advisor (CSA) is here to support you.
              </Typography>
            </Stack>
          </Stack>
        </Box>
        <Box
          sx={{ width: 'auto', bgcolor: 'white', padding: 2, borderRadius: 2 }}
        >
          <Stack direction="row" alignItems="center" spacing={2}>
            <OutboundOutlinedIcon fontSize="large" />
            <Stack>
              <Typography variant="h6" gutterBottom component="div">
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
