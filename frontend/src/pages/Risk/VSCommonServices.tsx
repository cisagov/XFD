import React from 'react';
import { useHistory } from 'react-router-dom';
import { ResponsiveCirclePacking } from '@nivo/circle-packing';
import { scaleLinear } from 'd3-scale';
import { Box, Paper } from '@mui/material';
import { Point } from 'types';
import * as RiskStyles from './style';

const VSCommonServices = (props: {
  title: string;
  data: Point[];
  type: string;
}) => {
  const history = useHistory();
  const { title, data, type } = props;
  const { cardRoot, cardMedium, header, chartSmall } = RiskStyles.classesRisk;
  const startColor = '#7BC9FF';
  const endColor = '#135787';

  const [smallest, largest] = data.reduce(
    (acc, cur) => {
      return [Math.min(acc[0], cur.value), Math.max(acc[1], cur.value)];
    },
    [Infinity, -Infinity]
  );

  const colorScale = scaleLinear<string>()
    .domain([smallest, largest])
    .range([startColor, endColor]);

  return (
    <Paper elevation={0} className={cardRoot}>
      <div className={cardMedium}>
        <div className={header}>
          <h2>{title}</h2>
        </div>
        <div className={chartSmall}>
          <Box sx={{ width: '100%', height: '100%' }}>
            <ResponsiveCirclePacking
              data={{ name: 'network-protocols', children: data }}
              margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
              id="id"
              value="value"
              colorBy="id"
              colors={({ value }) => colorScale(value)}
              leavesOnly={true}
              label={({ id, value }) => `${id}: ${value}`}
              padding={1}
              enableLabels={true}
              labelTextColor="white"
              onClick={(event) => {
                if (type === 'vulns') {
                  history.push(
                    `/inventory/vulnerabilities?severity=${event.id}`
                  );
                }
              }}
            />
          </Box>
        </div>
      </div>
    </Paper>
  );
};
export default VSCommonServices;
