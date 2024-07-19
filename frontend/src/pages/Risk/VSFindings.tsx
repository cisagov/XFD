import React from 'react';
import { Divider, Grid, Paper, Stack, Typography } from '@mui/material';
import { LocationCity, Groups, Place, Public } from '@mui/icons-material';
import * as RiskStyles from './style';
import { summaryData, vulnSummaryData } from 'test-utils/stats';

const VSFindings = () => {
  const { cardRoot, cardSmall, header, body } = RiskStyles.classesRisk;

  return (
    <Paper elevation={0} className={cardRoot}>
      <div className={cardSmall}>
        <div className={header}>
          <h2>VS High Level Findings</h2>
        </div>
        <div className={body}>
          <Grid container spacing={1}>
            <Grid item xs={12}>
              <Typography variant="button" fontSize={16} color="primary">
                Organization Details
              </Typography>
              <Divider color="primary" sx={{ border: 1 }} />
            </Grid>
            <Grid item xs={12}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <LocationCity />
                <Typography variant="body1">{summaryData?.org.name}</Typography>
              </Stack>
            </Grid>
            <Grid item xs={6}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <Public />
                <Typography variant="body1">
                  Region {summaryData?.org.regionId}
                </Typography>
              </Stack>
            </Grid>
            <Grid item xs={6}>
              {summaryData?.org.stateName && (
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Place />
                  <Typography variant="body1">
                    {summaryData?.org.stateName}
                  </Typography>
                </Stack>
              )}
            </Grid>
            <Grid item xs={12}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <Groups />
                <Typography variant="body1">
                  {summaryData?.org.members} Members
                </Typography>
              </Stack>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="button" fontSize={16} color="primary">
                Asset Details
              </Typography>
              <Divider color="primary" sx={{ border: 1 }} />
            </Grid>
            <Grid item xs={6}>
              <Typography variant="h6" display="inline">
                {summaryData?.org.rootDomainCount + ' '}
              </Typography>
              <Typography variant="body1" display="inline">
                Root Domains
              </Typography>
              <br />
              <Typography variant="h6" display="inline">
                {vulnSummaryData?.cred_breach_count + ' '}
              </Typography>
              <Typography variant="body1" display="inline">
                Breaches
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography variant="h6">
                  {vulnSummaryData?.inventory_count + ' '}
                </Typography>
                <Typography variant="body1">Assets Identified</Typography>
              </Stack>
              <Stack direction="row" alignItems="center" spacing={1}>
                <Typography variant="h6">
                  {vulnSummaryData?.dnstwist_vuln_count + ' '}
                </Typography>
                <Typography variant="body1">Emails Addresses</Typography>
              </Stack>
            </Grid>
          </Grid>
        </div>
      </div>
    </Paper>
  );
};
export default VSFindings;
