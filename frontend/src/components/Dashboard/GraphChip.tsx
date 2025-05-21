import React from 'react';
import { Chip } from '@mui/material';
import { Stack } from '@mui/system';

interface GraphChipProps {
  data: {
    label: string;
    onClick: () => void;
  }[];
  activeLabel: string;
}
const GraphChip: React.FC<GraphChipProps> = ({ data, activeLabel }) => {
  const capitalizeFirstLetter = (string: string) => {
    return string.charAt(0).toUpperCase() + string.slice(1);
  };
  return (
    <Stack
      direction="row"
      spacing={1}
      alignItems="center"
      role="radiogroup"
      aria-label="Data selector"
    >
      {data.map((item, index) => {
        const isActive = item.label === activeLabel;
        return (
          <Chip
            key={index}
            label={capitalizeFirstLetter(item.label)}
            variant={isActive ? 'graphOutlinedActive' : 'graphOutlinedInactive'}
            onClick={item.onClick}
            role="radio"
            aria-checked={isActive}
          />
        );
      })}
    </Stack>
  );
};
export default GraphChip;
