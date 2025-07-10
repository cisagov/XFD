import React from 'react';
import { Tabs, Tab } from '@mui/material';
import { useLocation, useHistory } from 'react-router-dom';

type NavTabItem = {
  title: string;
  path: string | { pathname: string };
  exact?: boolean;
};

type NavTabsProps = {
  items: NavTabItem[];
};

export const Subnav = ({ items }: NavTabsProps) => {
  const location = useLocation();
  const history = useHistory();

  const getPathString = (path: string | { pathname: string }) =>
    typeof path === 'string' ? path : path.pathname;

  const currentTab =
    items.find((item) =>
      item.exact
        ? location.pathname === getPathString(item.path)
        : location.pathname.startsWith(getPathString(item.path))
    )?.path ?? false;

  const handleChange = (_event: React.SyntheticEvent, newValue: string) => {
    const pathString = getPathString(newValue);
    history.push(pathString);
  };

  return (
    <Tabs
      value={currentTab}
      onChange={handleChange}
      aria-label="Findings section tabs"
      slotProps={{
        indicator: {
          sx: {
            height: 4,
            backgroundColor: 'primary.dark'
          }
        }
      }}
      sx={{
        minHeight: 'auto',
        mb: 3
      }}
    >
      {items.map((item) => (
        <Tab
          key={item.title}
          label={item.title}
          value={item.path}
          id={`tab-${item.path}`}
          aria-controls={`tabpanel-${item.path}`}
          sx={{
            minWidth: 'fit-content',
            px: 0,
            py: 1,
            mr: 3,
            mb: '3px',
            textTransform: 'none',
            color: 'neutrals.main',
            fontWeight: 600,
            fontSize: '16px',
            '&.Mui-selected': {
              color: 'primary.dark',
              fontWeight: 'bold'
            },
            '&:hover': {
              color: 'primary.darker'
            }
          }}
        />
      ))}
    </Tabs>
  );
};
