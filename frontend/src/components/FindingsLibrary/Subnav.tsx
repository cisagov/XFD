import React from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import { useLocation, Link } from 'react-router-dom';
import { useNavigationContext } from 'context/NavigationContext';
import { ROUTES } from '@/constants/routes';

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
  const { clearDrillDown } = useNavigationContext();

  const getPathString = (path: string | { pathname: string }) =>
    typeof path === 'string' ? path : path.pathname;

  const currentTab =
    items.find((item) =>
      item.exact
        ? location.pathname === getPathString(item.path)
        : location.pathname.startsWith(getPathString(item.path))
    )?.path ?? false;

  return (
    <Tabs
      value={currentTab}
      aria-label="Findings section tabs"
      sx={{
        minHeight: 'auto',
        mb: 3
      }}
    >
      {items.map((item) => {
        const pathString = getPathString(item.path);
        return (
          <Tab
            component={Link}
            to={item.path}
            onClick={() => {
              if (pathString === ROUTES.INVENTORY) {
                clearDrillDown();
              }
            }}
            key={item.title}
            label={item.title}
            value={item.path}
            sx={{
              minWidth: 'fit-content',
              px: 0,
              py: 1,
              mr: 3,
              mb: '3px'
            }}
          />
        );
      })}
    </Tabs>
  );
};
