import React from 'react';
import Notifications from 'pages/Notifications';
import Scan from 'pages/Scan/Scan';
import ScansView from 'pages/Scans/ScansView';
import ScanTasksView from 'pages/Scans/ScanTasksView';
import { Box, Container, Tab } from '@mui/material';
import { TabContext, TabList, TabPanel } from '@mui/lab';

export const AdminTools: React.FC = () => {
  const [value, setValue] = React.useState('1');

  const handleChange = (event: React.SyntheticEvent, newValue: string) => {
    setValue(newValue);
  };
  return (
    <Container maxWidth="lg" sx={{ py: '10px' }}>
      <Box sx={{ width: '100%', typography: 'body1' }}>
        <TabContext value={value}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <TabList onChange={handleChange} aria-label="lab API tabs example">
              <Tab label="Scans" value="1" />
              <Tab label="Scan History" value="2" />
              <Tab label="Notifications" value="3" />
            </TabList>
          </Box>
          <TabPanel value="1">
            <ScansView />
            <Scan />
          </TabPanel>
          <TabPanel value="2">
            <ScanTasksView />
          </TabPanel>
          <TabPanel value="3">
            <Notifications />
          </TabPanel>
        </TabContext>
      </Box>
    </Container>
  );
};

export default AdminTools;
