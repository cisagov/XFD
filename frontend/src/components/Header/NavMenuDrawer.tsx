import * as React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Box,
  Divider,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText
} from '@mui/material';

interface MenuItemType {
  menuItemTitle: string;
  path: string;
  users?: number;
  onClick?: () => void;
}

interface NavMenuDrawerProps {
  toggleDrawer: (open: boolean) => () => void;
  openDrawer: boolean;
  menuItems: { [section: string]: MenuItemType[] }[];
}
export const NavMenuDrawer: React.FC<NavMenuDrawerProps> = ({
  toggleDrawer,
  openDrawer,
  menuItems
}) => {
  const DrawerList = (
    <Box
      sx={{ width: 250 }}
      role="presentation"
      onClick={toggleDrawer(false)}
      onKeyDown={(e) => {
        if (e.key === 'Escape') toggleDrawer(false)();
      }}
    >
      <nav aria-label="Main navigation">
        <List>
          {menuItems.map((section, index) => {
            const entries = Object.entries(section);
            if (entries.length === 0) return null;

            const [sectionTitle, items] = entries[0];
            const menuTitle = (
              <ListItem role="presentation">
                <ListItemText
                  primary={
                    sectionTitle === 'Vulnerability Scanning'
                      ? 'Scanning Results'
                      : sectionTitle === 'Findings Library'
                        ? 'Inventory'
                        : sectionTitle
                  }
                  slotProps={{
                    primary: {
                      id: `drawer-section-${index}`,
                      sx: {
                        fontWeight: 'bold'
                      }
                    }
                  }}
                />
              </ListItem>
            );
            return (
              <React.Fragment key={index}>
                {menuTitle}
                {items.map((item, subIndex) => (
                  <ListItem
                    key={`${index}-${subIndex}`}
                    disablePadding
                    role="none"
                  >
                    <ListItemButton
                      component={NavLink}
                      to={item.path}
                      role="menuitem"
                      aria-label={item.menuItemTitle}
                    >
                      <ListItemText primary={item.menuItemTitle} />
                    </ListItemButton>
                  </ListItem>
                ))}

                <Divider />
              </React.Fragment>
            );
          })}
        </List>
      </nav>
    </Box>
  );

  return (
    <Drawer
      open={openDrawer}
      onClose={toggleDrawer(false)}
      anchor="right"
      role="dialog"
      aria-label="Navigation menu"
    >
      {DrawerList}
    </Drawer>
  );
};
