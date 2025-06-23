import React from 'react';
import { Box } from '@mui/system';
import InfoLabel from 'components/Dashboard/InfoLabel';
import { Subnav } from 'components';

const tooltipContentJson = [
  {
    id: 'Findings Library',
    content:
      'The Findings Library is a collection of all findings from your scans. You can search, filter, and sort through these findings to identify vulnerabilities and risks in your infrastructure.'
  }
];

interface FLHeaderProps {
  children?: React.ReactNode;
}

export const FindingsHeader: React.FC<FLHeaderProps> = ({ children }) => {
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
    <Box maxWidth="1152px" width="100%" margin="auto" sx={mobileMargin}>
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
      {children}
    </Box>
  );
};
