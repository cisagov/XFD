import classes from './Scans.module.scss';
import React from 'react';
import ScansView from './ScansView';
import ScanTasksView from './ScanTasksView';
import { Subnav } from 'components';
import { Switch, Route } from 'react-router-dom';
import { ROUTES } from '@/constants/routes';

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
