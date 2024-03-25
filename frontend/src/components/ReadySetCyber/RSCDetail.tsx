import React from 'react';
import { useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Button from '@mui/material/Button';
import { RSCSideNav } from './RSCSideNav';
import { RSCQuestion } from './RSCQuestion';
import { dummyResults } from './dummyData';
import { Typography } from '@mui/material';

export const RSCDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { questions } = dummyResults.find(
    (result) => result.id === parseInt(id)
  ) || { questions: [] };
  return (
    <Box sx={{ flexGrow: 1, padding: 2 }}>
      <Grid container spacing={2}>
        <Grid item xs={4}>
          <RSCSideNav />
        </Grid>
        <Grid item xs={8}>
          <Box sx={{ flexGrow: 1, padding: 2, backgroundColor: 'white' }}>
            <Stack>
              <Stack
                direction="row"
                justifyContent={'space-between'}
                alignItems="center"
                padding={2}
              >
                <Typography variant="h5" component="div">
                  Summary and Resources
                </Typography>
                <Button variant="contained" color="success">
                  Download PDF
                </Button>
              </Stack>
              <Divider />
              <h3>Thank you for completing the ReadySetCyber questionnaire!</h3>
              <p>
                Below, you’ll find a full summary of your completed
                ReadySetCyber questionnaire. Please note the areas where you can
                improve your organization’s cybersecurity posture, along with
                the recommended resources to help you address these areas. To
                take further action, contact your regional CISA Cybersecurity
                Advisor (CSA) for personalized support. You can also explore
                Crossfeed, CISA’s Attack Surface Management platform, for free
                vulnerability scanning services to kickstart or enhance your
                cybersecurity measures.
              </p>
              {questions.map((question) => (
                <RSCQuestion key={question.id} question={question} />
              ))}
            </Stack>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};
