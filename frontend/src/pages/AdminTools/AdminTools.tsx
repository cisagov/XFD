import React from 'react';
import classes from 'pages/Scans/Scans.module.scss';
import ScansView from 'pages/Scans/ScansView';
import ScanTasksView from 'pages/Scans/ScanTasksView';
import { Subnav } from 'components';
import { Switch, Route } from 'react-router-dom';

export const AdminTools: React.FC = () => {
  return (
    <>
      <Subnav
        items={[
          {
            title: 'Scans',
            path: `/admin-tools/scans`,
            exact: true
          },
          {
            title: 'Scan History',
            path: `/admin-tools/scans/history`,
            exact: true
          }
        ]}
      ></Subnav>
      <div className={classes.root}>
        <Switch>
          <Route path="/admin-tools/scans" exact>
            <ScansView />
          </Route>
          <Route path="/admin-tools/scans/history" exact>
            <ScanTasksView />
          </Route>
        </Switch>
      </div>
    </>
  );
};

export default AdminTools;
