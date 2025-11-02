import React from 'react';
import { FormGroup, FormControlLabel, Checkbox, useTheme } from '@mui/material';
import { styled } from '@mui/material/styles';

interface Props {
  options: { value: string; count: number }[];
  selected: string[];
  onSelect(value: string): void;
  onDeselect(value: string): void;
  disableScroll?: boolean;
}

export const FacetFilter: React.FC<Props> = (props) => {
  const { options, selected, onSelect, onDeselect, disableScroll } = props;
  const theme = useTheme();

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    value: string
  ) => {
    e.persist();
    if (e.target.checked) {
      onSelect(value);
    } else {
      onDeselect(value);
    }
  };

  return (
    <>
      <Root className={classes.root} disableScroll={disableScroll}>
        <FormGroup classes={{ root: classes.root }}>
          {options.map((opt) => (
            <FormControlLabel
              classes={{ label: classes.label, root: classes.root }}
              key={opt.value}
              control={
                <Checkbox
                  checked={selected.includes(opt.value)}
                  onChange={(e) => handleChange(e, opt.value)}
                  sx={{
                    '&.Mui-checked': {
                      color: theme.palette.primary.dark
                    }
                  }}
                />
              }
              label={
                <>
                  <span>{opt.value}</span>
                </>
              }
            />
          ))}
        </FormGroup>
      </Root>
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: 0
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 0,
            height: 24,
            pointerEvents: 'none',
            background:
              'linear-gradient(to bottom, rgba(255,255,255,0), #fff 90%)'
          }}
        />
      </div>
    </>
  );
};

//Styling
const PREFIX = 'FacetFilter';

const classes = {
  root: `${PREFIX}-root`,
  count: `${PREFIX}-count`,
  inp: `${PREFIX}-inp`,
  label: `${PREFIX}-label`,
  formControl: `${PREFIX}-formControl`
};

const Root = styled('div', {
  shouldForwardProp: (prop) => prop !== 'disableScroll'
})<{ disableScroll?: boolean }>(({ theme, disableScroll }) => ({
  [`&.${classes.root}`]: {
    width: '100%',
    paddingTop: 0,
    flexWrap: 'nowrap',
    maxHeight: 4.75 * 42, // 4.75 items of height 42px. Works with the gradient overlay.
    overflowY: disableScroll ? 'none' : 'scroll',
    scrollbarWidth: 'auto'
  },

  [`& .${classes.count}`]: {
    count: {}
  },

  [`& .${classes.inp}`]: {
    border: 'none',
    backgroundColor: '#fff',
    width: '100%',
    padding: '1rem',
    boxShadow: 'inset 0 1px 2px rgba(0,0,0,.39), 0 -1px 1px #FFF, 0 1px 0 #FFF'
  },

  [`& .${classes.label}`]: {
    width: '100%',
    display: 'flex',
    flexFlow: 'row nowrap',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '0.9rem',
    marginRight: 0,
    '& span': {
      display: 'inline-block'
    },
    '& $count': {
      fontSize: '0.7rem',
      color: theme.palette.grey[700]
    }
  },

  [`& .${classes.formControl}`]: {
    width: 'calc(100% + 8px)'
  }
}));
