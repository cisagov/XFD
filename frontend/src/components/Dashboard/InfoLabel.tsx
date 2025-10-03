import React from 'react';
import {
  Box,
  Typography,
  Link as MuiLink,
  SxProps,
  TypographyProps
} from '@mui/material';
import InfoTooltipIcon from './InfoTooltipIcon';
import { useHistory, useLocation } from 'react-router-dom';
import {
  useNavigationContext,
  isVSDashboard,
  isDrillDownDestination
} from 'context/NavigationContext';

type InfoLabelProps = {
  label: string;
  viewDetails?: boolean;
  link?: string;
  stateVariables?: {};
  typographyVariant?: TypographyProps['variant'];
  headingLevel?: 'h2' | 'h3' | 'p';
  tooltipContentJson: { content: string; id: string }[];
  labelStyle?: SxProps;
};

const InfoLabel: React.FC<InfoLabelProps> = ({
  label,
  viewDetails,
  link,
  typographyVariant = 'h2',
  headingLevel = 'h2',
  tooltipContentJson,
  stateVariables = {},
  labelStyle
}) => {
  const history = useHistory();
  const location = useLocation();
  const { markDrillDown } = useNavigationContext();

  const tooltipContent = (label: string): string => {
    const info = tooltipContentJson.find(
      (item: { id: string }) => item.id === label
    );
    return info ? info.content : 'No information available.';
  };

  const handleClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();

    // Only mark as drill-down if coming from VS Dashboard to a drill-down destination
    const isFromVSDashboard = isVSDashboard(location.pathname);
    const targetUrl = link || '/inventory';
    const isDrillDownTarget = isDrillDownDestination(targetUrl);

    if (isFromVSDashboard && isDrillDownTarget) {
      console.log(
        `[InfoLabel] Marking drill-down: ${location.pathname} → ${targetUrl}`
      );
      markDrillDown(location.pathname, targetUrl);
    }

    history.push(targetUrl, stateVariables);
  };

  return (
    <Box
      display="flex"
      alignItems="center"
      justifyContent="space-between"
      p={0}
    >
      <Box display="flex" alignItems="center">
        <Typography
          variant={typographyVariant}
          component={headingLevel}
          color="primary.darker"
          sx={labelStyle}
        >
          {label}
        </Typography>
        <InfoTooltipIcon label={label} tooltipContent={tooltipContent(label)} />
      </Box>
      {viewDetails && link && (
        <MuiLink href="#" onClick={handleClick}>
          <Typography variant="link" component="span" fontWeight="bold">
            View Details
          </Typography>
        </MuiLink>
      )}
    </Box>
  );
};

export default InfoLabel;
