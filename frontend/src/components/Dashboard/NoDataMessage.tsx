import React from 'react';
import { Paper, Typography } from '@mui/material';
import InfoOutlineIcon from '@mui/icons-material/InfoOutline';

interface NoDataMessageProps {
  userType: string;
  headerMsg?: string;
  customMessage?: React.ReactNode;
}
const NoDataMessage: React.FC<NoDataMessageProps> = ({
  userType = 'standard',
  headerMsg = 'No matching data available.',
  customMessage
}) => {
  const userTypeMessage =
    userType === 'globalAdmin' ||
    userType === 'regionalAdmin' ||
    userType === 'globalView'
      ? 'Please select another region or organization from the filter options.'
      : "Please use the 'Report a Bug' option in the Support menu to notify the CyHy team.";
  return (
    <Paper
      sx={{
        mx: 'auto',
        mt: '206px',
        p: 3,
        textAlign: 'center',
        maxWidth: '372px',
        minHeight: '186px'
      }}
    >
      <InfoOutlineIcon
        sx={{
          color: 'primary.dark',
          height: '40px',
          width: '40px'
        }}
      />
      <Typography variant="body2" fontSize="15px">
        {headerMsg}
      </Typography>
      <Typography variant="body2" fontSize="15px">
        {customMessage ?? userTypeMessage}
      </Typography>
    </Paper>
  );
};
export default NoDataMessage;
