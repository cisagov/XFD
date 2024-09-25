import React from 'react';
import { Box, Button, Tooltip } from '@mui/material';

export const SkipToMainContent: React.FC = () => {
  const handleClick = (event: any) => {
    event.preventDefault();
    const mainContentElement = document.getElementById('main-content');
    if (mainContentElement) {
      mainContentElement.focus(); // Programmatically set focus
    }
  };

  return (
    <Box sx={{ paddingLeft: 1 }}>
      <Button
        aria-label="Skip to main content"
        variant="text"
        tabIndex={0}
        onClick={handleClick}
        sx={{
          outline: 'true',
          fontSize: '0.6rem',
          padding: 0
        }}
      >
        Skip to main content
      </Button>
    </Box>
  );
};
