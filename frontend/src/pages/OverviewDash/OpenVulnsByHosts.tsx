import React, { useState } from 'react';
// import { useHistory } from 'react-router-dom';
import { Box } from '@mui/material';
import { axisClasses, BarChart } from '@mui/x-charts';
import { useTheme } from '@mui/material/styles';
import { getSeverityLevelColorMap } from 'utils/severityLevelColorMap';
import { transformOverviewHostData } from 'utils/transformOverviewHostData';
import InfoLabel from 'components/Dashboard/InfoLabel';
import infoIconContent from './infoIconContent.json';
import GraphChip from 'components/Dashboard/GraphChip';

const tooltipContentJson = infoIconContent.infoIconContent;

interface IncomingDataItem {
  id: string;
  value: number;
  label: string;
}

type SeverityLevelType = 'all' | 'low' | 'medium' | 'high' | 'critical';

const OpenVulnsByHostsBarChart = (props: any) => {
  return <BarChart {...props} />;
};
const OpenVulnsByHosts: React.FC<{ data: IncomingDataItem[] }> = ({ data }) => {
  const theme = useTheme();
  //   const history = useHistory();

  const capitalizeFirstLetter = (string: string) => {
    return string.charAt(0).toUpperCase() + string.slice(1);
  };

  const [severityLevel, setSeverityLevel] = useState<SeverityLevelType>('all');

  const graphChipData = ['all', 'critical', 'high', 'medium', 'low'].map(
    (type) => ({
      label: type,
      onClick: () => {
        setSeverityLevel(type as SeverityLevelType);
      }
    })
  );

  const sortedFilteredData = transformOverviewHostData(data, severityLevel);

  const severityLevelColorMap = getSeverityLevelColorMap(theme);
  const severityLevelColor =
    severityLevelColorMap[severityLevel as keyof typeof severityLevelColorMap];

  const barChart = (
    <OpenVulnsByHostsBarChart
      series={[
        {
          dataKey: 'value',
          label: capitalizeFirstLetter(severityLevel || ''),
          color: severityLevelColor
        }
      ]}
      dataset={sortedFilteredData}
      xAxis={[
        {
          dataKey: 'value',
          scaleType: 'linear',
          label: 'Number of Vulnerabilities',
          labelStyle: {
            fontSize: 12,
            fontStyle: 'italic',
            fontWeight: 500,
            color: theme.palette.neutrals.main
          },
          disableTicks: true,
          tickLabelStyle: { fontSize: 10 }
        }
      ]}
      yAxis={[
        {
          dataKey: 'hostName',
          scaleType: 'band',
          disableTicks: true,
          tickPlacement: 'middle',
          tickLabelPlacement: 'middle',
          tickLabelStyle: {
            fontSize: 12,
            fill: theme.palette.primary.dark,
            fontWeight: 500,
            textDecoration: 'underline',
            cursor: 'pointer'
          },
          categoryGapRatio: 0.6,
          width: 100
        }
      ]}
      height={300}
      layout="horizontal"
      margin={{ top: 20, right: 10, bottom: 20, left: 0 }}
      grid={{ vertical: true }}
      hideLegend
      slotProps={{
        // axisTickLabel: {
        //   onClick: (event: React.MouseEvent<SVGTextElement>) => {
        //     const tickLabel = event.currentTarget.textContent;
        //     const match = sortedFilteredData.find(
        //       (item) => item.hostName === tickLabel
        //     );
        //     const clickedHostId = match?.domainId;
        //     if (clickedHostId) {
        //       history.push(`/inventory/domain/${clickedHostId}`);
        //     } else {
        //       console.error('No matching domainId found for the clicked host');
        //     }
        //   }
        // },
        bar: ({ dataIndex }: { dataIndex: number }) => ({
          'aria-label': `Bar ${sortedFilteredData[dataIndex].hostName} with ${severityLevel} vulnerabilities`,
          tabIndex: 0, // Make bars focusable
          role: 'button',
          //   onClick: () => {
          //     const clickedHostId = sortedFilteredData[dataIndex].domainId;
          //     if (clickedHostId) {
          //       history.push(`/inventory/domain/${clickedHostId}`);
          //     } else {
          //       console.error('No matching domainId found for the clicked host');
          //     }
          //   },
          //   onKeyDown: (event: React.KeyboardEvent) => {
          //     if (event.key === 'Enter') {
          //       const clickedHostId = sortedFilteredData[dataIndex].domainId;
          //       if (clickedHostId) {
          //         history.push(`/inventory/domain/${clickedHostId}`);
          //       } else {
          //         console.error(
          //           'No matching domainId found for the clicked host'
          //         );
          //       }
          //     }
          //   },
          style: {
            cursor: 'pointer'
          }
        })
      }}
      sx={{
        [`.${axisClasses.root}`]: {
          [`.${axisClasses.line}`]: {
            strokeWidth: 3
          }
        }
      }}
    />
  );
  return (
    <Box
      border="1px solid"
      borderRadius="4px"
      borderColor="neutrals.light"
      px={3}
      py={2}
    >
      <InfoLabel
        label="Open Vulnerabilities by Hosts"
        typographyVariant="h3"
        headingLevel="h3"
        viewDetails
        link="/inventory/vulnerabilities"
        tooltipContentJson={tooltipContentJson}
      />
      <GraphChip data={graphChipData} activeLabel={severityLevel} />
      {data.length > 0 && barChart}
    </Box>
  );
};

export default OpenVulnsByHosts;
