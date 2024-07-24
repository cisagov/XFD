import React from 'react';
import { Grid, Paper, Typography } from '@mui/material';
import * as RiskStyles from './style';
import { wasFindingsData } from 'test-utils/stats';

const WASFindings = () => {
  const { cardRoot, cardSmall, header, body } = RiskStyles.classesRisk;
  const headerFontSize = { fontSize: '1.3rem' };
  return (
    <Paper elevation={0} className={cardRoot}>
      <div className={cardSmall}>
        <div className={header}>
          <h2>WAS High Level Findings</h2>
        </div>
        <div className={body}>
          <Grid container spacing={1}>
            <Grid item xs={12} pb={2}>
              <Typography variant="h6">
                Scan Date: {wasFindingsData.scanDate}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="h5" sx={headerFontSize}>
                ACTIVE VULNERABILITIES
              </Typography>
              <Typography variant="h4" color="error">
                {wasFindingsData.activeVulns}
              </Typography>
              <br />
              <Typography variant="h5" sx={headerFontSize}>
                REOPENED VULNERABILITIES
              </Typography>
              <Typography variant="h4" color="error">
                {wasFindingsData.reopenedVulns}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="h5" sx={headerFontSize}>
                NEW VULNERABILITIES
              </Typography>
              <Typography variant="h4" color="error">
                {wasFindingsData.newVulns}
              </Typography>
              <br />
              <Typography variant="h5" sx={headerFontSize}>
                SENSITIVE CONTENT
              </Typography>
              <Typography variant="h4" color="error">
                {wasFindingsData.sensitiveContent}
              </Typography>
            </Grid>
          </Grid>
        </div>
      </div>
    </Paper>
  );
};
export default WASFindings;
