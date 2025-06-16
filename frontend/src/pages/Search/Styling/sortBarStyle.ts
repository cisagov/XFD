import { styled } from '@mui/material/styles';
import { ContextType } from 'context/SearchProvider';
import { SavedSearch } from 'types';

const PREFIX = 'SortBar';

interface Props {
  sort_field: ContextType['sort_field'];
  sort_direction?: ContextType['sort_direction'];
  setSort: ContextType['setSort'];
  saveSearch?(): void;
  isFixed: boolean;
  existingSavedSearch?: SavedSearch;
  children?: React.ReactNode;
}

export const classes = {
  root: `${PREFIX}-root`,
  sortMenu: `${PREFIX}-sortMenu`,
  toggleDirection: `${PREFIX}-toggleDirection`,
  openFields: `${PREFIX}-openFields`,
  selectInp: `${PREFIX}-selectInp`,
  option: `${PREFIX}-option`
};

export const Root = styled('div')(() => ({
  [`&.${classes.root}`]: {
    zIndex: 100,
    display: 'flex',
    flexFlow: 'row nowrap',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0',
    color: '#4e4e4e',
    // margin: '0.5rem 0',
    boxShadow: ({ isFixed }: Props) =>
      isFixed ? '0px 1px 2px rgba(0, 0, 0, 0.15)' : 'none',
    transition: 'box-shadow 0.3s linear',
    '& *:focus': {
      outline: 'standard'
    },
    fontSize: 14
  },

  [`& .${classes.sortMenu}`]: {
    display: 'flex',
    flexFlow: 'row nowrap',
    alignItems: 'center',
    '& > span': {
      display: 'block'
    }
  },

  [`& .${classes.toggleDirection}`]: {
    '& > svg': {
      display: 'block',
      fontSize: '1rem',
      fontWeight: 600,
      color: '#4e4e4e'
    }
  },

  [`& .${classes.openFields}`]: {
    minWidth: 120,
    marginLeft: '0.5rem',
    '& :focus': {
      background: 'none'
    }
  },

  [`& .${classes.selectInp}`]: {
    fontWeight: 600,
    fontSize: 14,
    padding: 0,
    color: '#4e4e4e'
  },

  [`& .${classes.option}`]: {
    fontWeight: 600,
    fontSize: 14,
    color: '#4e4e4e'
  }
}));
