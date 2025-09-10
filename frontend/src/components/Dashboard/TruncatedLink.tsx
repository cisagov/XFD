import React from 'react';
import { Link, Tooltip, Typography } from '@mui/material';

interface TruncatedLinkProps {
  text: string | null;
  linkHandler: (value: string) => void;
  tooltipText?: string;
}

const TruncatedLink = ({
  text = '',
  linkHandler,
  tooltipText
}: TruncatedLinkProps) => {
  const safeText = text || '';
  const safeTooltipText = tooltipText || '';
  const showTooltip = safeTooltipText.length > 0;

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      linkHandler(safeText);
    }
  };

  return (
    <Tooltip
      title={showTooltip ? safeTooltipText : ''}
      placement={'right'}
      enterDelay={300}
      leaveDelay={200}
      describeChild
    >
      <Link
        onClick={() => linkHandler(safeText)}
        aria-label={`View details for: ${safeText}`}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        sx={{
          display: 'flex',
          cursor: 'pointer',
          alignItems: 'center'
        }}
      >
        <Typography
          variant="body2"
          component="span"
          color="inherit"
          sx={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            lineHeight: '1.5',
            maxHeight: '3em'
          }}
        >
          {safeText}
        </Typography>
      </Link>
    </Tooltip>
  );
};

export default TruncatedLink;
