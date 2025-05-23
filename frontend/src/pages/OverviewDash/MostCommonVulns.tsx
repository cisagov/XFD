import React from 'react';
import { useHistory } from 'react-router-dom';
import { Box, Link, Stack, Tooltip, Typography } from '@mui/material';
import { Circle } from '@mui/icons-material';
import RoundedTable from 'components/Dashboard/RoundedTable';
import { severityColor } from 'utils/severityLevelColorMap';
import InfoLabel from 'components/Dashboard/InfoLabel';
import infoIconContent from './infoIconContent.json';

type CommonVuln = {
  title: string | null;
  count: number;
  severity: string | null;
};

type ColumnConfig<T> = {
  key: keyof T;
  header: string;
  textAlign?: 'left' | 'center' | 'right';
  minWidth?: string;
  render: (value: T[keyof T], row: T) => React.ReactNode;
};

const tooltipContentJson = infoIconContent.infoIconContent;

export default function MostCommonVulns({ data }: { data: CommonVuln[] }) {
  const history = useHistory();
  const filteredVulnTableLinkHandler = (title: string) =>
    history.push('/inventory/vulnerabilities', { title: title });

  const TruncatedLink = ({ text = '' }: { text: string | null }) => (
    <Tooltip title={text} placement={'right'}>
      <Link
        onClick={() => filteredVulnTableLinkHandler(text || '')}
        aria-label={`View details for vulnerability: ${text}`}
        sx={{
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          lineHeight: '1.5',
          maxHeight: '3em',
          cursor: 'pointer'
        }}
      >
        {text}
      </Link>
    </Tooltip>
  );

  const mostCommonVulnsColumns: ColumnConfig<CommonVuln>[] = [
    {
      key: 'title',
      header: 'Vulnerability Name',
      minWidth: '100px',
      render: (value) => (
        <TruncatedLink text={value !== null ? String(value) : null} />
      )
    },
    {
      key: 'count',
      header: 'Host Counts',
      textAlign: 'center',
      render: (value) => (
        <Typography variant="body1" textAlign="center">
          {value}
        </Typography>
      )
    },
    {
      key: 'severity',
      header: 'Severity',
      textAlign: 'center',
      render: (value, row) => (
        <Stack direction="row" alignItems="center" justifyContent="center">
          <Circle
            sx={{
              color: severityColor(
                value !== null ? String(value).toLowerCase() : null
              ),
              fontSize: '18px',
              mr: 1,
              ...(value === 'Low' || value === 'Medium'
                ? { '& path': { stroke: '#646566', strokeWidth: 1.5 } }
                : {})
            }}
          />
          <Typography variant="body1" textTransform="capitalize">
            {value}
          </Typography>
        </Stack>
      )
    }
  ];

  return (
    <Box
      border="1px solid"
      borderRadius="4px"
      borderColor="neutrals.light"
      px={3}
      py={2}
    >
      <InfoLabel
        label="Most Common Vulnerabilities"
        typographyVariant="h3"
        headingLevel="h3"
        viewDetails
        link="/inventory/vulnerabilities"
        tooltipContentJson={tooltipContentJson}
      />
      <Box sx={{ height: 'auto', mt: -1.5 }}>
        <RoundedTable
          data={data.slice(0, 5)}
          columns={mostCommonVulnsColumns}
          noDataMessage="There were no vulnerabilities found."
        />
      </Box>
    </Box>
  );
}
