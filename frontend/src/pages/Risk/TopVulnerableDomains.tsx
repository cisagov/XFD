import React from 'react';
import { ResponsiveBar } from '@nivo/bar';
import { Chip, Pagination, Tooltip } from '@mui/material';
import { Point, VulnSeverities } from './Risk';
import { useState } from 'react';
import { Link, useHistory } from 'react-router-dom';
import {
  sevLabels,
  resultsPerPage,
  getSeverityColor,
  severities,
  getAllVulnColor
} from './utils';
import * as RiskStyles from './style';

const TopVulnerableDomains = (props: { data: Point[] }) => {
  const history = useHistory();
  const { data } = props;
  const {
    header,
    chip,
    note,
    cardBig,
    seeAll,
    chartLarge,
    chipWrapper,
    chartHeader,
    footer
  } = RiskStyles.classesRisk;
  const [current, setCurrent] = useState(1);
  const [labels, setLabels] = useState(sevLabels);
  const keys = sevLabels;
  const pageStart = (current - 1) * resultsPerPage;
  // Store for count by total vulns
  const domainTotals: { [key: string]: number } = {};
  // Separate count by severity but also store total vulns
  const domainToSevMap: any = {};
  for (const point of data) {
    const split = point.id.split('|');
    const domain = split[0];
    const severity = split[1];
    if (labels.includes(severity)) {
      if (!(domain in domainToSevMap)) domainToSevMap[domain] = {};
      if (!(domain in domainTotals)) domainTotals[domain] = 0;
      domainToSevMap[domain][severity] = point.value;
      domainTotals[domain] += point.value;
    }
  }
  const domainsWithVulns = Object.keys(domainToSevMap).length;
  const dataVal = Object.keys(domainToSevMap)
    .map((key) => ({
      label: key,
      Total: domainTotals[key],
      ...domainToSevMap[key]
    }))
    .sort((a, b) => {
      let diff = b.Total - a.Total;
      if (diff === 0) {
        for (const label of sevLabels) {
          diff += (label in b ? b[label] : 0) - (label in a ? a[label] : 0);
          if (diff !== 0) break;
        }
      }
      return diff;
    })
    .slice(pageStart, Math.min(pageStart + 30, domainsWithVulns))
    .reverse();
  // Repurposes the "All" chip to show total vulns vs aggregate
  const allVuln = labels.length === 5;
  //Custom Bar Layer to allow for top to bottom tab navigation
  const CustomBarLayer = ({ bars }: { bars: any[]; [key: string]: any }) => {
    const reversedBars = [...bars].reverse();
    return reversedBars.map((bar) => (
      <Tooltip
        arrow
        title={
          <span>
            {' '}
            {bar.data.value} {bar.data.id}{' '}
            {bar.data.value > 1 ? 'vulnerabilites' : 'vulnerability'} in Domain:{' '}
            {bar.data.indexValue}{' '}
          </span>
        }
        key={bar.key}
        placement="right"
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
            aria-label={` ${bar.data.value} ${bar.data.id}${' '}
          ${
            bar.data.value > 1 ? 'vulnerabilites' : 'vulnerability'
          } in Domain:${' '}
          ${bar.data.indexValue}`}
            onClick={() => {
              history.push(
                `/inventory/vulnerabilities?domain=${bar.data.label}&severity=${bar.data.id}`
              );
            }}
          />
        </g>
      </Tooltip>
    ));
  };
  return (
    <div className={cardBig}>
      <div className={seeAll}>
        <p>
          <Link to="/inventory/vulnerabilities">See All Vulnerabilities</Link>
        </p>
      </div>
      <div className={header}>
        <h2>Open Vulnerabilities by Domain</h2>
      </div>
      <div className={chartLarge}>
        {data.length === 0 ? (
          <h3>No open vulnerabilities</h3>
        ) : (
          <>
            <p className={note}>*Top 50 domains with open vulnerabilities</p>
            <div className={chipWrapper}>
              {severities.map((sevFilter: VulnSeverities, i: number) => (
                <Chip
                  key={i}
                  className={chip}
                  disabled={sevFilter.disable}
                  label={sevFilter.label}
                  onClick={() => {
                    setLabels(sevFilter.sevList);
                    setCurrent(1);
                  }}
                ></Chip>
              ))}
            </div>
            <div className={chartHeader}>
              <h5>Domain&emsp; Breakdown</h5>
              <h5 style={{ textAlign: 'right', paddingLeft: 0 }}>Total</h5>
            </div>
            <ResponsiveBar
              tabIndex={0}
              data={dataVal as any}
              //If all vuln is selected, only show total vulns
              keys={allVuln ? ['Total'] : keys}
              layers={['grid', 'axes', CustomBarLayer, 'markers', 'legends']}
              indexBy="label"
              margin={{
                top: 10,
                right: 40,
                bottom: 150,
                left: 260
              }}
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
              //If all vuln is selected, only show color for total vulns
              colors={allVuln ? getAllVulnColor : (getSeverityColor as any)}
              borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
              axisTop={null}
              axisRight={null}
              axisBottom={{
                ariaHidden: true,
                tickSize: 0,
                tickPadding: 5,
                tickRotation: 0,
                legend: '',
                legendPosition: 'middle',
                legendOffset: 40
              }}
              axisLeft={{
                ariaHidden: true,
                tickSize: 0,
                tickPadding: 20,
                tickRotation: 0,
                legend: '',
                legendPosition: 'middle',
                legendOffset: -65
              }}
              animate={true}
              ariaLabel={
                'Top Vulnerable Domains - y-axis: Domain Name, x-axis: Count of Open Vulnerabilities'
              }
              enableGridX={true}
              enableGridY={false}
              enableLabel={false}
              isFocusable={true}
              layout={'horizontal'}
              motionDamping={15}
              {...({ motionStiffness: 90 } as any)}
            />
          </>
        )}
      </div>
      <div className={footer}>
        <span>
          <strong>
            {(domainsWithVulns === 0
              ? 0
              : (current - 1) * resultsPerPage + 1
            ).toLocaleString()}{' '}
            -{' '}
            {Math.min(
              (current - 1) * resultsPerPage + resultsPerPage,
              domainsWithVulns
            ).toLocaleString()}
          </strong>{' '}
          of <strong>{domainsWithVulns.toLocaleString()}</strong>
        </span>
        <Pagination
          count={Math.ceil(domainsWithVulns / resultsPerPage)}
          page={current}
          onChange={(_, page) => setCurrent(page)}
          color="primary"
          size="small"
        />
      </div>
    </div>
  );
};
export default TopVulnerableDomains;
