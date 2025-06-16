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
      <Box sx={{ height: '100px' }} />
      <nav aria-label="Main navigation">
        <List>
          {menuItems.map((section, index) => {
            const entries = Object.entries(section);
            if (entries.length === 0) return null;

            const [, items] = entries[0];

            return (
              <React.Fragment key={index}>
                {/* {menuTitle} */}
                {items &&
                  items.length > 0 &&
                  items.map((item, subIndex) => {
                    const isExternalLink =
                      item.path?.startsWith('http') ||
                      item.path?.startsWith('mailto');
                    return (
                      <ListItem
                        key={`${index}-${subIndex}`}
                        disablePadding
                        role="none"
                      >
                        {item.onClick ? (
                          //Used for buttons with onClick handlers
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
                        ) : isExternalLink ? (
                          // Used for external links
                          <ListItemButton
                            component="a"
                            href={item.path}
                            target={
                              item.path.startsWith('http')
                                ? '_blank'
                                : undefined
                            }
                            rel={
                              item.path.startsWith('http')
                                ? 'noopener noreferrer'
                                : undefined
                            }
                            role="menuitem"
                            aria-label={item.menuItemTitle}
                            onClick={toggleDrawer(false)}
                          >
                            <ListItemText primary={item.menuItemTitle} />
                          </ListItemButton>
                        ) : (
                          // Used for internal links
                          <ListItemButton
                            component={NavLink}
                            to={item.path}
                            role="menuitem"
                            aria-label={item.menuItemTitle}
                            onClick={toggleDrawer(false)}
                          >
                            <ListItemText primary={item.menuItemTitle} />
                          </ListItemButton>
                        )}
                      </ListItem>
                    );
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
