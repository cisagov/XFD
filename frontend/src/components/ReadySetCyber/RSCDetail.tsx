import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import { RSCSideNav } from './RSCSideNav';
import { Category, Entry, RSCQuestion } from './RSCQuestion';
import { useAuthContext } from 'context';

export const RSCDetail: React.FC = () => {
  const { apiGet } = useAuthContext();
  const { id } = useParams<{ id: string }>();
  const [categories, setCategories] = useState<Category[]>([]);

  const fetchResult = useCallback(async () => {
    try {
      const data = await apiGet(`/assessments/${id}`);
      console.log('API Response:', data); // Continue to log the data for verification
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        const transformedCategories = Object.entries(data).map(
          ([name, entries]) => ({
            name,
            entries: entries as Entry[]
          })
        );
        setCategories(transformedCategories);
      } else {
        console.error('Unexpected response format:', data);
        setCategories([]); // Fallback to an empty array if the format isn't correct
      }
    } catch (e) {
      console.error('Failed to fetch categories:', e);
      setCategories([]); // Ensure categories is reset to an empty array on error
    }
  }, [apiGet, id]);

  useEffect(() => {
    fetchResult();
  }, [fetchResult]);
  console.log('Transformed categories:', categories);

  return (
    <Box sx={{ flexGrow: 1, padding: 2 }}>
      <Grid container spacing={2}>
        <Grid item xs={4}>
          <RSCSideNav categories={categories} />
        </Grid>
        <Grid item xs={8}>
          <Box sx={{ flexGrow: 1, padding: 2, backgroundColor: 'white' }}>
            <Stack spacing={2}>
              <Stack
                direction="row"
                justifyContent="space-between"
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
              <Typography variant="h6" component="h3" gutterBottom>
                Thank you for completing the ReadySetCyber questionnaire!
              </Typography>
              <Typography>
                Below, you’ll find a full summary of your completed
                ReadySetCyber questionnaire. Please note the areas where you can
                improve your organization’s cybersecurity posture, along with
                the recommended resources to help you address these areas. To
                take further action, contact your regional CISA Cybersecurity
                Advisor (CSA) for personalized support. You can also explore
                Crossfeed, CISA’s Attack Surface Management platform, for free
                vulnerability scanning services to kickstart or enhance your
                cybersecurity measures.
              </Typography>
              {categories.map((category, index) => (
                <RSCQuestion key={index} categories={[category]} />
              ))}
            </Stack>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};
