import React from 'react';
import { useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Button from '@mui/material/Button';
import { RSCSideNav } from './RSCSideNav';
import { RSCResult } from './RSCResult';
import { RSCQuestion } from './RSCQuestion';
import { dummyResults } from './dummyData';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

export const RSCDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const result = dummyResults.find((result) => result.id === parseInt(id)) || {
    id: 0,
    type: '',
    date: ''
  };
  const { questions } = dummyResults.find(
    (result) => result.id === parseInt(id)
  ) || { questions: [] };

  const categories =
    dummyResults.find((result) => result.id === parseInt(id))?.categories || [];

  const printRef = React.useRef<HTMLDivElement>(null);

  const handleDownloadPDF = async () => {
    if (printRef.current) {
      const canvas = await html2canvas(printRef.current);
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF();
      pdf.addImage(imgData, 'PNG', 0, 0, 210, 297); // Fix: Use the overload that expects 8 arguments
      pdf.save('download.pdf');
    }
  };

  return (
    <Box sx={{ flexGrow: 1, padding: 2 }} ref={printRef}>
      <Grid container spacing={2}>
        <Grid item sm={4} sx={{ display: { xs: 'none', sm: 'grid' } }}>
          <RSCSideNav />
        </Grid>
        <Grid item xs={12} sm={8}>
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
                <Button
                  variant="contained"
                  color="success"
                  onClick={handleDownloadPDF}
                >
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
              <Box>
                <RSCResult
                  id={result.id}
                  type={result.type}
                  date={result.date}
                  categories={[]}
                  questions={[]}
                />
              </Box>
              <br />
              <Accordion sx={{ display: { xs: 'block', sm: 'none' } }}>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="panel1a-content"
                  id="panel1a-header"
                >
                  {' '}
                  Categories
                </AccordionSummary>
                {categories.map((category) => (
                  <AccordionDetails key={category.id}>
                    {category.name}
                  </AccordionDetails>
                ))}
              </Accordion>
              <br />
              <Stack spacing={2}>
                {questions.map((question) => (
                  <RSCQuestion key={question.id} question={question} />
                ))}
              </Stack>
            </Stack>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};
