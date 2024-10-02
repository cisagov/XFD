import { styled } from '@mui/material/styles';

const PREFIX = 'FilterTags';

export const classes = {
  chip: `${PREFIX}-chip`
};

export const Root = styled('div')(({ theme }) => ({
  [`& .${classes.chip}`]: {
    marginTop: '0.5rem',
    marginRight: '0.5rem'
  }
}));
