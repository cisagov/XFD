import React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { useHistory } from 'react-router-dom';
import { ROUTES } from '@/constants/routes';

interface ErrorPageProps {
  code: '403' | '404';
  title: string;
  message: string;
}

export const ErrorPage: React.FC<ErrorPageProps> = ({
  code,
  title,
  message
}) => {
  const history = useHistory();

  return (
    <Box
      component="main"
      sx={{
        alignItems: 'center',
        display: 'flex',
        justifyContent: 'center',
        minHeight: '60vh',
        p: 3,
        width: '100%'
      }}
    >
      <Paper
        elevation={2}
        sx={{ maxWidth: 560, p: { xs: 3, sm: 5 }, textAlign: 'center' }}
      >
        <Typography color="primary" component="p" variant="h1">
          {code}
        </Typography>
        <Typography component="h1" gutterBottom variant="h4">
          {title}
        </Typography>
        <Typography color="text.secondary" paragraph>
          {message}
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button onClick={() => history.goBack()} variant="outlined">
            Go Back
          </Button>
          <Button onClick={() => history.push(ROUTES.HOME)} variant="contained">
            Go Home
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};
