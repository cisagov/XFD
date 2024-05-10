import React from 'react';
import Card from '@mui/material/Card';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import { ButtonBase, Typography } from '@mui/material';
import { useHistory } from 'react-router-dom';

interface Props {
  id: string;
  type: string;
  createdAt: string;
  updatedAt: string;
  rscID: string;
}

export const RSCResult: React.FC<Props> = (props) => {
  const { id, type, createdAt: date } = props;
  const history = useHistory();
  const handleClick = () => {
    history.push(`/readysetcyber/result/${id}`);
  };
  return (
    <ButtonBase onClick={handleClick}>
      <Card
        style={{ outline: 'standard', cursor: 'pointer' }}
        sx={{ width: '100%' }}
      >
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
    </ButtonBase>
  );
};
