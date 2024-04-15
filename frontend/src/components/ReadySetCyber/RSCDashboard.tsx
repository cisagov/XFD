import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import { RSCSideNav } from './RSCSideNav';
import { RSCResult } from './RSCResult';
import { dummyResults } from './dummyData';

const results = dummyResults;

export const RSCDashboard: React.FC = () => {
  return (
    <Box sx={{ flexGrow: 1, padding: 2 }}>
      <Grid container spacing={2}>
        <Grid item sm={4} sx={{ display: { xs: 'none', sm: 'grid' } }}>
          <RSCSideNav />
        </Grid>
        <Grid item xs={12} sm={8}>
          <Box sx={{ flexGrow: 1, padding: 2, backgroundColor: 'white' }}>
            <Stack>
              <h2>Assessment Results</h2>
              <Divider />
              <h3>Thank you for completing the ReadySetCyber questionnaire!</h3>
              <p>
                Below, you’ll find a summary of all completed ReadySetCyber
                questionnaires. Selecting a result will allow you to review
                areas where you can improve your organization’s cybersecurity
                posture, along with recommended resources to help address those
                areas. To take further action, contact your regional CISA
                Cybersecurity Advisor (CSA) for personalized support. You can
                also explore Crossfeed, CISA’s Attack Surface Management
                platform, for free vulnerability scanning services to kickstart
                or enhance your cybersecurity measures.
              </p>
              <Stack spacing={2}>
                {results.map((result) => (
                  <RSCResult
                    key={result.id}
                    id={result.id}
                    type={result.type}
                    date={result.date}
                    categories={result.categories}
                    questions={result.questions}
                  />
                ))}
              </Stack>
              <Divider />
            </Stack>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};
