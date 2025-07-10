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
import { MenuItemType } from './Header';

interface NavMenuDrawerProps {
  toggleDrawer: (open: boolean) => () => void;
  openDrawer: boolean;
  menuItems: { [section: string]: MenuItemType[] }[];
  onMenuItemClick?: (item: MenuItemType) => Promise<void>;
}

export const NavMenuDrawer: React.FC<NavMenuDrawerProps> = ({
  toggleDrawer,
  openDrawer,
  menuItems,
  onMenuItemClick
}) => {
  const DrawerList = (
    <Box
      sx={{ width: 250 }}
      role="presentation"
      onKeyDown={(e) => {
        if (e.key === 'Escape') toggleDrawer(false)();
      }}
    >
      <Box sx={{ height: '100px' }} />
      <nav aria-label="Main navigation">
        <List>
          {menuItems.map((section, index) => {
            const entries = Object.entries(section);
            if (entries.length === 0) return null;

            const [, items] = entries[0];

            return (
              <React.Fragment key={index}>
                {items &&
                  items.length > 0 &&
                  items.map((item, subIndex) => {
                    const isHttpLink = item.path?.startsWith('http');
                    const isMailtoLink = item.path?.startsWith('mailto:');

                    // 1. onClick handler
                    if (item.onClick) {
                      return (
                        <ListItem
                          key={`${index}-${subIndex}`}
                          disablePadding
                          role="none"
                        >
                          <ListItemButton
                            role="menuitem"
                            aria-label={item.menuItemTitle}
                            onClick={() => {
                              item.onClick && item.onClick();
                              toggleDrawer(false)();
                            }}
                          >
                            <ListItemText primary={item.menuItemTitle} />
                          </ListItemButton>
                        </ListItem>
                      );
                    }

                    // 2. Object store handler
                    if (item.objectStoreParams && onMenuItemClick) {
                      return (
                        <ListItem
                          key={`${index}-${subIndex}`}
                          disablePadding
                          role="none"
                        >
                          <ListItemButton
                            role="menuitem"
                            aria-label={item.menuItemTitle}
                            onClick={async () => {
                              await onMenuItemClick(item);
                              toggleDrawer(false)();
                            }}
                          >
                            <ListItemText primary={item.menuItemTitle} />
                          </ListItemButton>
                        </ListItem>
                      );
                    }

                    // 3. External http link
                    if (isHttpLink) {
                      return (
                        <ListItem
                          key={`${index}-${subIndex}`}
                          disablePadding
                          role="none"
                        >
                          <ListItemButton
                            component="a"
                            href={item.path}
                            target="_blank"
                            rel="noopener noreferrer"
                            role="menuitem"
                            aria-label={item.menuItemTitle}
                            onClick={toggleDrawer(false)}
                          >
                            <ListItemText primary={item.menuItemTitle} />
                          </ListItemButton>
                        </ListItem>
                      );
                    }

                    // 4. External mailto link
                    if (isMailtoLink) {
                      return (
                        <ListItem
                          key={`${index}-${subIndex}`}
                          disablePadding
                          role="none"
                        >
                          <ListItemButton
                            component="a"
                            href={item.path}
                            target="_blank"
                            rel="noopener noreferrer"
                            role="menuitem"
                            aria-label={item.menuItemTitle}
                          >
                            <ListItemText primary={item.menuItemTitle} />
                          </ListItemButton>
                        </ListItem>
                      );
                    }
                    // 5. Internal link
                    if (item.path) {
                      return (
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
                            onClick={toggleDrawer(false)}
                          >
                            <ListItemText primary={item.menuItemTitle} />
                          </ListItemButton>
                        </ListItem>
                      );
                    }
                    return null;
                  })}
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
