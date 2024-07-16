import React from 'react';
import { Box, Button } from '@mui/material';
import { fontSize } from '@mui/system';

export const SkipToMainContent: React.FC = () => {
  const handleClick = (event: any) => {
    event.preventDefault(); // Prevent default anchor behavior
    const mainContentElement = document.getElementById('main-content');
    if (mainContentElement) {
      mainContentElement.focus(); // Programmatically set focus
    } else {
      document.getElementById('inventory-content')?.focus();
    }
  };

  return (
    <Box sx={{ paddingLeft: 1 }}>
      <a
        href="#main-content"
        className="skip-to-main-content"
        onClick={handleClick}
      >
        <Button
          tabIndex={0}
          sx={{
            outline: 'true',
            fontSize: 10,
            padding: 0
          }}
        >
          Skip to main content
        </Button>
      </a>
    </Box>
  );
};
