import React from 'react';
import { Paper, Typography } from '@mui/material';
import InfoOutlineIcon from '@mui/icons-material/InfoOutline';

interface NoDataMessageProps {
  userType: string;
}
const NoDataMessage: React.FC<NoDataMessageProps> = ({
  userType = 'standard'
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
        p: 4,
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
        No matching data available.
      </Typography>
      <Typography variant="body2" fontSize="15px">
        {userTypeMessage}
      </Typography>
    </Paper>
  );
};
export default NoDataMessage;
