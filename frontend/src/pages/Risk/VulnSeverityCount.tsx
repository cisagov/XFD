import React from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { useHistory } from 'react-router-dom';
import * as RiskStyles from './style';
import { Paper } from '@mui/material';
import { scaleLinear } from 'd3-scale';
import { SummaryStats } from 'types';

const VulnSeverityCount = (props: { data: SummaryStats | undefined }) => {
  const history = useHistory();
  const { data } = props;
  const { cardRoot, cardSmall, header, chartSmall } = RiskStyles.classesRisk;

  let severityArray: any[] = [];
  if (data) {
    severityArray = Object.entries(data?.severity);
  }
  const transformedData = severityArray.map(([id, value]) => ({ id, value }));

  const getMinMaxValues = (transformedData: any[]): [number, number] => {
    const values = transformedData
      .filter((item) => item.value !== null)
      .map((item: { value: any }) => item.value);
    return [Math.min(...values), Math.max(...values)];
  };
  const colorScale = scaleLinear<string>()
    .domain(getMinMaxValues(transformedData))
    .range(['#7BC9FF', '#135787']);

  return (
    <Paper elevation={0} className={cardRoot}>
      <div className={cardSmall}>
        <div className={header}>
          <h2>Vulnerability Severities</h2>
        </div>
        <div className={chartSmall}>
          <ResponsiveBar
            data={transformedData}
            colors={({ value }) => colorScale(value ?? 0)}
            keys={['value']}
            indexBy="id"
            margin={{ top: 30, right: 40, bottom: 75, left: 100 }}
            theme={{
              fontSize: 12,
              axis: {
                legend: {
                  text: {
                    fontWeight: 'bold'
                  }
                }
              }
            }}
            onClick={() => {
              history.push(`/inventory/vulnerabilities`);
              window.location.reload();
            }}
            padding={0.5}
            borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
            axisTop={null}
            axisRight={null}
            axisBottom={{
              tickSize: 0,
              tickPadding: 5,
              tickRotation: 0,
              legend: 'Severity',
              legendPosition: 'middle',
              legendOffset: 40
            }}
            axisLeft={{
              tickSize: 0,
              tickPadding: 20,
              tickRotation: 0,
              legend: 'Count',
              legendPosition: 'middle',
              legendOffset: -65
            }}
            animate={true}
            enableLabel={false}
            motionDamping={15}
            enableGridX={false}
            enableGridY={true}
            {...({ motionStiffness: 90 } as any)}
          />
        </div>
      </div>
    </Paper>
  );
};
export default VulnSeverityCount;
