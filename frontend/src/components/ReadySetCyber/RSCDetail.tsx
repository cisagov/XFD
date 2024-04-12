import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Button from '@mui/material/Button';
import { RSCSideNav } from './RSCSideNav';
import { RSCResult } from './RSCResult';
import { RSCQuestion } from './RSCQuestion';
import { Typography } from '@mui/material';
import { useAuthContext } from 'context';

export const RSCDetail: React.FC = () => {
  const { apiGet } = useAuthContext();
  const { id } = useParams<{ id: string }>();
  const [details, setDetails] = React.useState<any>({});

  const fetchResult = useCallback(async () => {
    try {
      const data = await apiGet(`/assessments/${id}`);
      // console.log(data["Data Security"]);
      // console.log(data["Data Security"][0]);
      // console.log(data["Data Security"][0]["question"]);
      // console.log(data["Data Security"][0]["question"].longForm);

      setDetails(data);
    } catch (e) {
      console.error(e);
    }
  }, [apiGet, id]);

  useEffect(() => {
    fetchResult();
  }, [fetchResult]);

  const dataSecurity = details['Data Security'];

  // console.log("Key 0: ", Object.keys(data)[0]);

  // console.log("This is Security: ", dataSecurity[0]);
  // console.log("Details: ", typeof details);
  // for (const question in data) {
  //   console.log(question);
  // }

  // Object.keys(data).forEach((key)=> {
  //   console.log(key, dataSecurity[key]);
  // }
  // );

  // Object.keys(details).forEach((key)=> {
  //   console.log(key, details[key]);
  //   // Object.keys(details[key]).forEach((key2)=> {
  //   //   console.log(key2, details[key][key2]);
  //   // });
  // });

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
              <Box>
                {/* <RSCResult
                  id={result.id}
                  type={result.type}
                  createdAt={result.date}
                  categories={[]}
                  questions={[]}
                /> */}
              </Box>
              {/* {console.log("Details: ", details)} */}
              {/* {details.forEach((detail) => {
                  <>
                  <RSCQuestion key={detail.id} question={detail} />
                  <br />
                </>
                }); */}
              <div>
                {Object.entries(details).map(([detail]) => (
                  // <div key={detail}>
                  //   <strong>{detail}:</strong>
                  // </div>
                  <RSCQuestion key={detail} category={details} />
                ))}
              </div>
            </Stack>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};
