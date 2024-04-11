import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';

interface Props {
  question: {
    id: number;
    title: string;
    answers: {
      id: number;
      name: string;
      selected: boolean;
    }[];
    category: string;
  };
}

export const RSCQuestion: React.FC<Props> = (props) => {
  const question = props.question;
  const answers = props.question.answers;
  return (
    <Box
      sx={{ width: 'auto', bgcolor: '#D3D3D3', padding: 2, borderRadius: 2 }}
    >
      <Stack spacing={2}>
        <Typography variant="h6" gutterBottom component="div">
          Question {question.id}
        </Typography>
        <Typography variant="h6" gutterBottom component="div">
          {question.title}
        </Typography>
        <Stack
          direction="row"
          spacing={2}
          sx={{ display: { xs: 'none', sm: 'flex' } }}
        >
          {answers.map((answer) => (
            <Button key={answer.id} variant="contained" color="primary">
              {answer.name}{' '}
            </Button>
          ))}
        </Stack>
        <Grid container spacing={2} alignSelf={'flex-end'}>
          {answers.map((answer) => (
            <Grid
              item
              xs={6}
              key={answer.id}
              sx={{ display: { xs: 'grid', sm: 'none' } }}
            >
              <Button variant="contained" color="primary">
                {answer.name}{' '}
              </Button>
            </Grid>
          ))}
        </Grid>
        <Box
          sx={{
            width: '100%',
            bgcolor: 'background.paper',
            padding: 2,
            borderRadius: 2
          }}
        >
          <h3>Recommended Resources</h3>
          <h4>Resource Type</h4>
          <h5>Resource Title</h5>
          <p>Resource Description</p>
        </Box>
      </Stack>
    </Box>
  );
};
