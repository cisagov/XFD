import React, { useState, useMemo } from 'react';
import { styled, useTheme } from '@mui/material/styles';
import { Box, Button, Chip } from '@mui/material';
import { Check } from '@mui/icons-material';

const PREFIX = 'TaggedArrayInput';

const classes = {
  form: `${PREFIX}-form`,
  icon: `${PREFIX}-icon`,
  inner: `${PREFIX}-inner`,
  inp: `${PREFIX}-inp`,
  chip: `${PREFIX}-chip`,
  tagsWrapper: `${PREFIX}-tagsWrapper`,
  error: `${PREFIX}-error`
};

const Root = styled('form')(({ theme }) => ({
  [`&.${classes.form}`]: {
    width: '100%',
    background: 'none'
  },

  [`& .${classes.inner}`]: {
    flex: '1',
    maxWidth: 1400,
    margin: '0 auto',
    background: 'none',
    position: 'relative'
  },

  [`& .${classes.inp}`]: {
    padding: '0.5rem 0.5rem 0.5rem 0.5rem',
    display: 'block',
    width: '100%',
    border: '1px solid',
    borderRadius: '5px',
    borderColor: theme.palette.neutrals.main,
    height: '45px',
    fontSize: '1rem',
    fontWeight: 300,
    background: 'none',
    '&::placeholder': {
      color: theme.palette.neutrals.main
    }
  },

  [`& .${classes.icon}`]: {
    fontSize: '1.5rem',
    color: theme.palette.neutrals.white
  },

  [`& .${classes.chip}`]: {
    margin: '2px 0'
  },

  [`& .${classes.tagsWrapper}`]: {
    display: 'block',
    margin: '1rem 0'
  },

  [`& .${classes.error}`]: {
    display: 'block',
    margin: 0,
    paddingTop: '0.2rem',
    color: theme.palette.error.light
  }
}));

interface Props {
  placeholder?: string;
  values: string[];
  onAddTag(value: string): void;
  onRemoveTag(value: string): void;
}

export const TaggedArrayInput: React.FC<Props> = (props) => {
  const { values, onAddTag, onRemoveTag, placeholder = '' } = props;
  const [inpValue, setInpValue] = useState('');
  const theme = useTheme();

  const error = useMemo(
    () => (values.includes(inpValue) ? 'Filters must be unique' : ''),
    [values, inpValue]
  );

  const onSubmit: React.FormEventHandler = (e) => {
    e.preventDefault();
    if (!error && inpValue !== '') {
      onAddTag(inpValue);
      setInpValue('');
    }
  };

  const onRemove = (key: string) => {
    onRemoveTag(key);
  };

  const onInpChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    e.persist();
    setInpValue(e.target.value);
  };

  return (
    <Root onSubmit={onSubmit} className={classes.form}>
      <Box className={classes.inner}>
        <input
          className={classes.inp}
          value={inpValue}
          onChange={onInpChange}
          aria-label="Filter"
          placeholder={placeholder}
        />
        <Box
          sx={{
            position: 'absolute',
            right: '0.01rem',
            top: '50%',
            transform: 'translateY(-50%)',
            backgroundColor: theme.palette.primary.dark,
            height: '100%',
            width: '20%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderTopRightRadius: '5px',
            borderBottomRightRadius: '5px',
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: theme.palette.primary.darker,
              cursor: 'pointer'
            },
            tabIndex: 0
          }}
        >
          <Button
            type="submit"
            sx={{
              height: '100%',
              width: '20%',
              borderRadius: '0 5px 5px 0'
            }}
            disabled={!!error || inpValue === ''}
            onClick={onSubmit}
          >
            <Check className={classes.icon} />
          </Button>
        </Box>
      </Box>
      {error && <span className={classes.error}>{error}</span>}
      <div className={classes.tagsWrapper}>
        {values.map((val) => (
          <div key={val}>
            <Chip
              classes={{ root: classes.chip }}
              label={val}
              onDelete={() => onRemove(val)}
            />
          </div>
        ))}
      </div>
    </Root>
  );
};
