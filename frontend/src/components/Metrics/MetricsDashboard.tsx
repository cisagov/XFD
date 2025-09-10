import React from 'react';
import { Box } from '@mui/material';
import ScansWidget from './Widgets/ScansWidget';

const MetricsDashboard: React.FC = () => {
  return (
    <Box p={2}>
      <ScansWidget />
    </Box>
  );
};

export default MetricsDashboard;
