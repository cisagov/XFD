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
import { RSCNextSteps } from './RSCNextSteps';
import { RSCAccordionNav } from './RSCAccordionNav';
import { FloatingNav } from './FloatingNav';
import { ScrollTop } from './ScrollTop';
import { useReactToPrint } from 'react-to-print';

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

  const printRef = React.useRef<HTMLDivElement>(null);

  const handleDownloadPDF = useReactToPrint({
    content: () => printRef.current,
    documentTitle: `ReadySetCyber Summary ${new Date().toLocaleDateString()}`
  });

  return (
    <>
      <Box sx={{ flexGrow: 1, padding: 2 }}>
        <Grid container spacing={2}>
          <Grid item sm={4} sx={{ display: { xs: 'none', sm: 'grid' } }}>
            <RSCSideNav categories={categories} />
          </Grid>
          <Grid item xs={12} sm={8}>
            <Box sx={{ marginBottom: 2, display: { sm: 'none' } }}>
              <RSCAccordionNav categories={categories} />
            </Box>
            <Stack spacing={2}>
              <Box
                sx={{
                  flexGrow: 1,
                  padding: 2,
                  backgroundColor: 'white'
                }}
                ref={printRef}
              >
                <Stack spacing={2}>
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                  >
                    <Typography
                      variant="h3"
                      component="div"
                      style={{ color: '#003E67', fontWeight: 'bold' }}
                    >
                      Summary and Resources
                    </Typography>
                    <Button
                      variant="contained"
                      color="success"
                      onClick={handleDownloadPDF}
                      sx={{ '@media print': { display: 'none' } }}
                    >
                      Download PDF
                    </Button>
                  </Stack>
                  <Divider />
                  <Typography variant="h6" component="h3" gutterBottom>
                    Thank you for completing the ReadySetCyber questionnaire!
                  </Typography>
                  <Typography>
                    Below, you’ll find a full summary of your completed
                    ReadySetCyber questionnaire. Please note the areas where you
                    can improve your organization’s cybersecurity posture, along
                    with the recommended resources to help you address these
                    areas. To take further action, contact your regional CISA
                    Cybersecurity Advisor (CSA) for personalized support. You
                    can also explore Crossfeed, CISA’s Attack Surface Management
                    platform, for free vulnerability scanning services to
                    kickstart or enhance your cybersecurity measures.
                  </Typography>
                  {categories.map((category, index) => (
                    <RSCQuestion key={index} categories={[category]} />
                  ))}
                </Stack>
              </Box>
              <RSCNextSteps />
            </Stack>
          </Grid>
        </Grid>
      </Box>
      <FloatingNav categories={categories} />
      <ScrollTop />
    </>
  );
};
