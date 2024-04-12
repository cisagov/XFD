import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';

interface Props {
  category: {
    question: {
      id: string;
      longForm: string;
      number: string;
    };
    selection: string;
  };
}

export const RSCQuestion: React.FC<Props> = (props) => {
  const question = props.category.question;
  const category = props.category;
  const answers = props.category.selection;

  console.log(
    'Question: ',
    Object.entries(category).map(([key, value]) => ({
      key,
      value
    }))
  );

  return (
    <div>
      <Box
        sx={{ width: '100%', bgcolor: '#D3D3D3', padding: 2, borderRadius: 2 }}
      >
        {/* <Typography variant="h6" gutterBottom component="div">
          Question {question.number}
        </Typography> */}
        <Typography variant="h6" gutterBottom component="div">
          {question.longForm}
        </Typography>
        <Stack direction="row" spacing={2} padding={2} paddingLeft={0}>
          <Button key={answers} variant="contained" color="primary">
            {answers}{' '}
          </Button>
        </Stack>
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
      </Box>
    </div>
  );
};
