import React from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { Point } from './Risk';
import { useHistory } from 'react-router-dom';
import { getSingleColor } from './utils';
import * as RiskStyles from './style';
import { Paper, Tooltip } from '@mui/material';

const TopVulnerablePorts = (props: { data: Point[] }) => {
  const CustomBarLayer = ({ bars }: { bars: any[]; [key: string]: any }) => {
    const reversedBars = [...bars].reverse();
    return reversedBars.map((bar) => (
      <Tooltip
        title={
          <span>
            {bar.data.value} domains with vulnerabilities on port{' '}
            {bar.data.indexValue}
          </span>
        }
        placement="right"
        arrow
        key={bar.key}
      >
        <g key={bar.key}>
          <rect
            role="button"
            key={bar.key}
            x={bar.x}
            y={bar.y}
            width={bar.width}
            height={bar.height}
            fill={bar.color}
            tabIndex={0}
            aria-label={`${
              bar.data.value
            }${' '}domains with vulnerabilities on port${' '}
            ${bar.data.indexValue}`}
            //To-do: Fix onClick so that User is routed to Inventory page with Port # pre-selected as a filter
            onClick={() => {
              console.log('clicked label value: ', bar);
              history.push(
                `/inventory?filters[0][field]=services.port&filters[0][values][0]=n_${bar.data.indexValue}_n&filters[0][type]=any`
              );
              window.location.reload();
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                history.push(
                  `/inventory?filters[0][field]=services.port&filters[0][values][0]=n_${bar.data.indexValue}_n&filters[0][type]=any`
                );
                window.location.reload();
              }
            }}
          />
        </g>
      </Tooltip>
    ));
  };
  const history = useHistory();
  const { data } = props;
  const { cardRoot, cardSmall, header, chartSmall } = RiskStyles.classesRisk;
  const dataVal = data
    .reverse()
    .map((e) => ({ ...e, [['Port'][0]]: e.value })) as any;
  return (
    <Paper elevation={0} className={cardRoot}>
      <div className={cardSmall}>
        <div className={header}>
          <h2>Most Common Ports</h2>
        </div>
        <div className={chartSmall}>
          <ResponsiveBar
            data={dataVal as any}
            keys={['Port']}
            layers={['grid', 'axes', CustomBarLayer]}
            indexBy="label"
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
            padding={0.5}
            colors={getSingleColor}
            borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
            axisTop={null}
            axisRight={null}
            axisBottom={{
              ariaHidden: true,
              tickSize: 0,
              tickPadding: 5,
              tickRotation: 0,
              legend: 'Count',
              legendPosition: 'middle',
              legendOffset: 40
            }}
            axisLeft={{
              ariaHidden: true,
              tickSize: 0,
              tickPadding: 20,
              tickRotation: 0,
              legend: 'Port',
              legendPosition: 'middle',
              legendOffset: -65
            }}
            animate={true}
            ariaLabel={'Top Vulnerable Ports - y-axis: Port, x-axis: Count'}
            enableGridX={true}
            enableGridY={false}
            enableLabel={false}
            isFocusable={true}
            layout={'horizontal'}
            motionDamping={15}
            {...({ motionStiffness: 90 } as any)}
          />
        </div>
      </div>
    </Paper>
  );
};
export default TopVulnerablePorts;
