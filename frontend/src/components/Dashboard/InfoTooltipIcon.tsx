import React from 'react';
import { Divider, Paper, Tooltip, IconButton, Typography } from '@mui/material';
import InfoOutlined from '@mui/icons-material/InfoOutlined';

type InfoTooltipIconProps = {
  label: string;
  // data: { content: string; id: string }[];
  tooltipContent: string;
};

const InfoTooltipIcon: React.FC<InfoTooltipIconProps> = ({
  label,
  tooltipContent
}) => {
  // const getTooltipContent = (label: string): string => {
  //   const info = data.find((item: { id: string }) => item.id === label);
  //   return info ? info.content : 'No information available.';
  // };
  const tooltipContentJSX = (
    <Paper
      elevation={3}
      sx={{ p: 0, backgroundColor: 'background.paper', width: '100%' }}
    >
      <Typography
        variant="uiElementsII"
        component="p"
        color="neutrals.black"
        sx={{ p: 2 }}
      >
        {label}
      </Typography>
      <Divider sx={{ width: '100%', borderColor: 'neutrals.main' }} />
      <Typography
        variant="uiElementsII"
        component="p"
        color="neutrals.main"
        sx={{ p: 2 }}
      >
        {/* {getTooltipContent(label)} */}
        {tooltipContent}
      </Typography>
    </Paper>
  );
  return (
    <Tooltip
      title={tooltipContentJSX}
      placement="right"
      enterDelay={300}
      leaveDelay={200}
      describeChild
      slotProps={{
        tooltip: {
          sx: {
            backgroundColor: 'transparent',
            boxShadow: 'none',
            padding: 0
          }
        }
      }}
    >
      <IconButton
        aria-label={`More information about ${label}`}
        disableRipple
        disableFocusRipple
        sx={{
          p: 2,
          width: '56px',
          height: '56px'
        }}
      >
        <InfoOutlined sx={{ fontSize: 24 }} />
      </IconButton>
    </Tooltip>
  );
};

export default InfoTooltipIcon;
