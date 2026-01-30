import React from 'react';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import FilterAlt from '@mui/icons-material/FilterAlt';
import { useFilterDrawerContext } from 'context/FilterDrawerContext';

const FilterDrawerToggle: React.FC = () => {
  const {
    isFilterDrawerOpen,
    setIsFilterDrawerOpen,
    selectedRegionId,
    selectedOrgName
  } = useFilterDrawerContext();

  const handleToggle = () => {
    setIsFilterDrawerOpen(!isFilterDrawerOpen);
  };
  const [committedRegionId, setCommittedRegionId] = React.useState<
    string | null
  >(null);
  const [committedOrgName, setCommittedOrgName] = React.useState<string | null>(
    null
  );
  const prevOrgNameRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    // Ensure org name is not null and has changed before updating committed state
    if (selectedOrgName && selectedOrgName !== prevOrgNameRef.current) {
      setCommittedOrgName(selectedOrgName);
      setCommittedRegionId(selectedRegionId);
      prevOrgNameRef.current = selectedOrgName;
    }
  }, [selectedOrgName, selectedRegionId]);

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
          aria-label="Toggle Filter Drawer"
        >
          Filter
        </Button>
        {committedRegionId && (
          <>
            <Typography
              variant="filterStatCallout"
              sx={{ color: 'primary.darker', ml: 3 }}
            >
              Region:
            </Typography>
            <Typography
              variant="filterStatCallout"
              sx={{ color: 'primary.dark', ml: '4px' }}
            >
              {committedRegionId}
            </Typography>
          </>
        )}

        {committedRegionId && committedOrgName && (
          <Box
            aria-hidden
            sx={{
              height: 18,
              width: '1px',
              backgroundColor: 'neutrals.light',
              mx: '8px',
              alignSelf: 'center'
            }}
          />
        )}

        {committedOrgName && (
          <>
            <Typography
              variant="filterStatCallout"
              sx={{ color: 'primary.darker' }}
            >
              Organization:
            </Typography>
            <Typography
              variant="filterStatCallout"
              sx={{ color: 'primary.dark', ml: '4px' }}
            >
              {committedOrgName}
            </Typography>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default FilterDrawerToggle;
