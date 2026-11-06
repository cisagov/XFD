// React
import React from 'react';
import { Switch, Route } from 'react-router-dom';

// Material-UI Components
import ScanTasksView from './ScanTasksView';
import ScansView from './ScansView';
import { Subnav } from '@/components';

// Constants
import { ROUTES } from '@/constants/routes';

// Styles
import classes from './Scans.module.scss';

export const Scans: React.FC = () => {
  return (
    <>
      <Subnav
        items={[
          {
            title: 'Scans',
            path: ROUTES.SCANS,
            exact: true
          },
          {
            title: 'Scan History',
            path: ROUTES.SCANS_HISTORY,
            exact: true
          }
        ]}
      ></Subnav>
      <div className={classes.root}>
        <Switch>
          <Route path={ROUTES.SCANS} exact>
            <ScansView />
          </Route>
          <Route path={ROUTES.SCANS_HISTORY} exact>
            <ScanTasksView />
          </Route>
        </Switch>
      </div>
    </>
  );
};

export default Scans;
