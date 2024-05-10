import React, { useEffect, useCallback } from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import { RSCDefaultSideNav } from './RSCDefaultSideNav';
import { RSCResult } from './RSCResult';
import { useAuthContext } from 'context';

export const RSCDashboard: React.FC = () => {
  const { apiGet } = useAuthContext();

  const [results, setResults] = React.useState<
    {
      id: string;
      createdAt: string;
      updatedAt: string;
      rscID: string;
      type: string;
    }[]
  >([]);

  const fetchResults = useCallback(async () => {
    try {
      const data = await apiGet('/assessments');
      console.log(data);
      setResults(data);
    } catch (e) {
      console.error(e);
    }
  }, [apiGet]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  console.log(results);

  return (
    <Box sx={{ flexGrow: 1, padding: 2 }}>
      <Grid container spacing={2}>
        <Grid item sm={4} sx={{ display: { xs: 'none', sm: 'grid' } }}>
          <RSCDefaultSideNav />
        </Grid>
        <Grid item xs={12} sm={8}>
          {results.length === 0 ? (
            <Box sx={{ flexGrow: 1, padding: 2, backgroundColor: 'white' }}>
              <h2>Welcome to ReadySetCyber Dashboard</h2>
              <Divider />
              <h3>Thank you for registering with RSC Dashboard!</h3>
              <p>
                It appears you have not completed the ReadySetCyber
                questionnaire yet or your assessment is still processing.
              </p>
              <p>
                If you have not completed the questionnaire, please look to the
                menu to your left and click on &quot;Take Questionnaire
                Again&quot;. This will redirect you to ReadySetCyber where you
                can complete a questionnaire.
              </p>
              <p>
                If you have already completed the questionnaire, please check
                back later to view your assessment.
              </p>
            </Box>
          ) : (
            <Box sx={{ flexGrow: 1, padding: 2, backgroundColor: 'white' }}>
              <Stack>
                <h2>Assessment Results</h2>
                <Divider />
                <h3>
                  Thank you for completing the ReadySetCyber questionnaire!
                </h3>
                <p>
                  Below, you’ll find a summary of all completed ReadySetCyber
                  questionnaires. Selecting a result will allow you to review
                  areas where you can improve your organization’s cybersecurity
                  posture, along with recommended resources to help address
                  those areas. To take further action, contact your regional
                  CISA Cybersecurity Advisor (CSA) for personalized support. You
                  can also explore Crossfeed, CISA’s Attack Surface Management
                  platform, for free vulnerability scanning services to
                  kickstart or enhance your cybersecurity measures.
                </p>
                <Stack spacing={2}>
                  {results.map((result) => (
                    <RSCResult
                      key={result.id}
                      id={result.id}
                      type={result.type}
                      createdAt={result.createdAt}
                      updatedAt={result.updatedAt}
                      rscID={result.rscID}
                    />
                  ))}
                </Stack>
              </Stack>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};
