import React from 'react';
import Card from '@mui/material/Card';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import { Typography } from '@mui/material';
import { useHistory } from 'react-router-dom';

interface Props {
  id: number;
  type: string;
  date: string;
  categories: {
    id: number;
    name: string;
  }[];
  questions: {
    id: number;
    title: string;
    answers: {
      id: number;
      name: string;
      selected: boolean;
    }[];
  }[];
}

export const RSCResult: React.FC<Props> = (props) => {
  const { id, type, date } = props;
  const history = useHistory();
  const handleClick = () => {
    history.push(`/readysetcyber/result/${id}`);
  };
  return (
    <Card onClick={handleClick}>
      <Box sx={{ width: '100%', bgcolor: 'background.paper', p: 2 }}>
        <Stack
          direction="row"
          justifyContent={'space-between'}
          alignItems="center"
        >
          <Typography variant="h5" component="div">
            {type}
          </Typography>
          <Typography variant="h5">{date}</Typography>
        </Stack>
      </Box>
    </Card>
  );
};
