import React from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Tab from '@mui/material/Tab';
import TabContext from '@mui/lab/TabContext';
import TabList from '@mui/lab/TabList';
import TabPanel from '@mui/lab/TabPanel';
import Notifications from 'pages/Notifications';
import ScansView from 'pages/Scans/ScansView';
import ScanTasksView from 'pages/Scans/ScanTasksView';
import Metrics from '../../components/Metrics/MetricsDashboard';
import QueueMonitorView from 'pages/Scans/QueueMonitorView';
import { Logs } from 'components/Logs/Logs';

export const AdminTools: React.FC = () => {
  const [value, setValue] = React.useState('1');

  const handleChange = (event: React.SyntheticEvent, new_value: string) => {
    setValue(new_value);
  };
  return (
    <Container maxWidth="xl" sx={{ py: 1 }}>
      <Box sx={{ width: '100%', typography: 'body1' }}>
        <TabContext value={value}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <TabList onChange={handleChange} aria-label="lab API tabs example">
              <Tab label="Scans" value="1" />
              <Tab label="Scan History" value="2" />
              <Tab label="Queue Monitoring" value="3" />
              <Tab label="Notifications" value="4" />
              <Tab label="User Logs" value="5" />
              <Tab label="Metrics" value="6" />
            </TabList>
          </Box>
          <TabPanel value="1">
            <ScansView />
          </TabPanel>
          <TabPanel value="2">
            <ScanTasksView />
          </TabPanel>
          <TabPanel value="3">
            <QueueMonitorView />
          </TabPanel>
          <TabPanel value="4">
            <Notifications />
          </TabPanel>
          <TabPanel value="5">
            <Logs />
          </TabPanel>
          <TabPanel value="6">
            <Metrics />
          </TabPanel>
        </TabContext>
      </Box>
    </Container>
  );
};

export default AdminTools;
