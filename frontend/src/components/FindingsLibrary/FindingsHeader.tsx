import React from 'react';
import { Box } from '@mui/system';
import InfoLabel from 'components/Dashboard/InfoLabel';
import { Subnav } from 'components';

const tooltipContentJson = [
  {
    id: 'Findings Library',
    content:
      'The Findings Library is a collection of all findings, concerning your organization and its assets. You can search, filter, and sort through these findings to identify vulnerabilities and risks in your infrastructure.'
  }
];

export const FindingsHeader: React.FC = () => {
  const mobileMargin = {
    px: {
      xs: 1,
      sm: 1,
      md: 1,
      lg: 1,
      xl: 0
    }
  };

  return (
    <Box width="100%" sx={mobileMargin}>
      <Box sx={{ my: '40px' }}>
        <InfoLabel
          label="Findings Library"
          typographyVariant="h1"
          viewDetails
          tooltipContentJson={tooltipContentJson}
        />
      </Box>
      <Subnav
        items={[
          { title: 'Search Results', path: '/inventory', exact: true },
          { title: 'Domains', path: '/inventory/domains' },
          { title: 'Vulnerabilities', path: '/inventory/vulnerabilities' }
        ]}
      />
    </Box>
  );
};
