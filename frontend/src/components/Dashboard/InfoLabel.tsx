import React from 'react';
import {
  Box,
  Typography,
  Link as MuiLink,
  TypographyProps
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import InfoTooltipIcon from './InfoTooltipIcon';

type InfoLabelProps = {
  label: string;
  viewDetails?: boolean;
  link?: string;
  typographyVariant?: TypographyProps['variant'];
  headingLevel?: 'h2' | 'h3' | 'p';
  tooltipContentJson: { content: string; id: string }[];
};

const InfoLabel: React.FC<InfoLabelProps> = ({
  label,
  viewDetails,
  link,
  typographyVariant = 'h2',
  headingLevel = 'h2',
  tooltipContentJson
}) => {
  const tooltipContent = (label: string): string => {
    const info = tooltipContentJson.find(
      (item: { id: string }) => item.id === label
    );
    return info ? info.content : 'No information available.';
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
        >
          {label}
        </Typography>
        <InfoTooltipIcon label={label} tooltipContent={tooltipContent(label)} />
      </Box>

      {viewDetails && link && (
        <MuiLink to={link} component={RouterLink}>
          <Typography variant="link" component="p" fontWeight="bold">
            View Details
          </Typography>
        </MuiLink>
      )}
    </Box>
  );
};

export default InfoLabel;
