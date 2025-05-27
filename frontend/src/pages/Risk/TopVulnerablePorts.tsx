import React from 'react';
import { useHistory } from 'react-router-dom';
import { Paper } from '@mui/material';
import { BarChart, axisClasses } from '@mui/x-charts';
import { useTheme } from '@mui/material/styles';
import * as RiskStyles from './style';
import { Point } from './OverviewDash';

export const TopVulnerablePorts = (props: { data: Point[] }) => {
  const { data } = props;
  const { cardRoot, cardSmall, chartSmall } = RiskStyles.classesRisk;
  const theme = useTheme();
  const history = useHistory();

  const chartData = data.map((item) => ({
    port: item.label,
    value: item.value
  }));

  const barColor = theme.palette.primary.main;

  return (
    <Paper elevation={0} className={cardRoot}>
      <div className={cardSmall}>
        <div className={chartSmall} style={{ height: 300 }}>
          <BarChart
            series={[
              {
                dataKey: 'value',
                label: 'Ports',
                color: barColor
              }
            ]}
            dataset={chartData}
            xAxis={[
              {
                dataKey: 'value',
                scaleType: 'linear',
                label: 'Numer of Vulnerabilities',
                labelStyle: {
                  fontSize: 12,
                  fontStyle: 'italic',
                  fontWeight: 500,
                  color:
                    theme.palette.neutrals?.main || theme.palette.text.primary
                },
                disableTicks: true,
                tickLabelStyle: { fontSize: 10 }
              }
            ]}
            yAxis={[
              {
                dataKey: 'port',
                scaleType: 'band',
                label: 'Port Number',
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
                width: 90
              }
            ]}
            height={300}
            layout="horizontal"
            margin={{ top: 20, right: 10, bottom: 20, left: 0 }}
            grid={{ vertical: true }}
            hideLegend
            slotProps={{
              axisTickLabel: {
                onClick: (event: React.MouseEvent<SVGTextElement>) => {
                  const dataIndex = parseInt(
                    event.currentTarget.getAttribute('data-index') || '0',
                    10
                  );
                  const clickedPort = chartData[dataIndex]?.port;
                  if (clickedPort) {
                    history.push(`/inventory?port=${clickedPort}`);
                  }
                }
              },

              bar: ({ dataIndex }: { dataIndex: number }) => ({
                'aria-label': `Bar for port ${chartData[dataIndex].port} with ${chartData[dataIndex].value} vulnerable domains`,
                tabIndex: dataIndex,
                role: 'button',
                onClick: () => {
                  history.push(`/inventory?port=${chartData[dataIndex].port}`);
                },
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
              },
              '.MuiChartsGrid-line': {
                strokeDasharray: '4 4',
                stroke: theme.palette.neutrals.light
              }
            }}
          />
        </div>
      </div>
    </Paper>
  );
};
export default TopVulnerablePorts;
