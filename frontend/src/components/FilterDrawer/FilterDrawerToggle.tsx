import React from 'react';
import { useFilterDrawerContext } from 'context/FilterDrawerContext';
import { AppBar, Button, Toolbar } from '@mui/material';
import { FilterAlt } from '@mui/icons-material';

const FilterDrawerToggle: React.FC = () => {
  const { isFilterDrawerOpen, setIsFilterDrawerOpen } =
    useFilterDrawerContext();

  const handleToggle = () => {
    setIsFilterDrawerOpen(!isFilterDrawerOpen);
  };

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        margin: 'auto',

        px: {
          xs: 1,
          sm: 1,
          md: 1,
          lg: 1,
          xl: 0
        },
        backgroundColor: 'neutrals.white',
        borderBottom: '0.5px solid',
        borderColor: 'neutrals.light',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '84px'
      }}
    >
      <Toolbar disableGutters sx={{ maxWidth: '1152px', width: '100%', p: 0 }}>
        <Button
          variant="primaryContained"
          onClick={handleToggle}
          startIcon={<FilterAlt />}
        >
          Filter
        </Button>
      </Toolbar>
    </AppBar>
  );
};

export default FilterDrawerToggle;
