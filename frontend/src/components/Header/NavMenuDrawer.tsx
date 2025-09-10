import * as React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Box,
  Collapse,
  Divider,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import { MenuItemType } from './Header';
import { useTheme } from '@mui/material/styles';

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
  const [openCollapse, setOpenCollapse] = React.useState<string | false>(false);
  const [openSubCollapse, setOpenSubCollapse] = React.useState<string | false>(
    false
  );
  const theme = useTheme();
  const DrawerList = (
    <Box
      sx={{ width: 250, pt: 0 }}
      role="presentation"
      onKeyDown={(e) => {
        if (e.key === 'Escape') toggleDrawer(false)();
      }}
    >
      <nav aria-label="Main navigation">
        <List disablePadding>
          {menuItems.map((section, index) => {
            const entries = Object.entries(section);
            if (entries.length === 0) return null;

            const [sectionTitle, items] = entries[0];
            const isDropdownSection = [
              'Learning Center',
              'Support',
              'Admin Hub'
            ].includes(sectionTitle);

            // Section dropdown for Learning Center, Support, Admin Hub
            if (isDropdownSection) {
              return (
                <React.Fragment key={index}>
                  <ListItem disablePadding role="presentation">
                    <ListItemButton
                      onClick={() => {
                        setOpenCollapse(
                          openCollapse === sectionTitle ? false : sectionTitle
                        );
                      }}
                      aria-haspopup="true"
                      aria-expanded={openCollapse === sectionTitle}
                      sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <ListItemText
                        primary={
                          <Typography
                            variant="globalNav"
                            sx={{
                              color:
                                openCollapse === sectionTitle
                                  ? theme.palette.primary.darker
                                  : theme.palette.primary.dark
                            }}
                          >
                            {sectionTitle}
                          </Typography>
                        }
                      />
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          marginLeft: 'auto',
                          color:
                            openCollapse === sectionTitle
                              ? theme.palette.primary.darker
                              : theme.palette.primary.dark
                        }}
                      >
                        {openCollapse === sectionTitle ? (
                          <KeyboardArrowUpIcon />
                        ) : (
                          <KeyboardArrowDownIcon />
                        )}
                      </ListItemIcon>
                    </ListItemButton>
                  </ListItem>
                  <Collapse
                    in={openCollapse === sectionTitle}
                    timeout="auto"
                    unmountOnExit
                  >
                    <List component="div" disablePadding sx={{ pl: 1 }}>
                      {items &&
                        items.length > 0 &&
                        items.map((item, subIndex) => {
                          const isHttpLink = item.path?.startsWith('http');
                          const isMailtoLink = item.path?.startsWith('mailto:');
                          const isSubMenu =
                            item.subMenuItems && item.subMenuItems.length > 0;

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
                                  <ListItemText
                                    primary={
                                      <Typography
                                        variant="globalNav"
                                        sx={{
                                          color: 'primary.dark'
                                        }}
                                      >
                                        {item.menuItemTitle}
                                      </Typography>
                                    }
                                  />
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
                                  <ListItemText
                                    primary={
                                      <Typography
                                        variant="globalNav"
                                        sx={{
                                          color: 'primary.dark'
                                        }}
                                      >
                                        {item.menuItemTitle}
                                      </Typography>
                                    }
                                  />
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
                                  <ListItemText
                                    primary={
                                      <Typography
                                        variant="globalNav"
                                        sx={{
                                          color: 'primary.dark'
                                        }}
                                      >
                                        {item.menuItemTitle}
                                      </Typography>
                                    }
                                  />
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
                                  <ListItemText
                                    primary={
                                      <Typography
                                        variant="globalNav"
                                        sx={{
                                          color: 'primary.dark'
                                        }}
                                      >
                                        {item.menuItemTitle}
                                      </Typography>
                                    }
                                  />
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
                                  <ListItemText
                                    primary={
                                      <Typography
                                        variant="globalNav"
                                        sx={{
                                          color: 'primary.dark'
                                        }}
                                      >
                                        {item.menuItemTitle}
                                      </Typography>
                                    }
                                  />
                                </ListItemButton>
                              </ListItem>
                            );
                          }

                          // 6. Submenu
                          if (isSubMenu && onMenuItemClick) {
                            return (
                              <React.Fragment key={`${index}-${subIndex}`}>
                                <ListItem disablePadding role="none">
                                  <ListItemButton
                                    onClick={() => {
                                      setOpenSubCollapse(
                                        openSubCollapse ===
                                          `${index}-${subIndex}`
                                          ? false
                                          : `${index}-${subIndex}`
                                      );
                                    }}
                                    role="menuitem"
                                    aria-haspopup="true"
                                    aria-label={item.menuItemTitle}
                                  >
                                    <ListItemText
                                      sx={{ flex: 1 }}
                                      primary={
                                        <Typography
                                          variant="subMenuText"
                                          sx={{
                                            color:
                                              openSubCollapse ===
                                              `${index}-${subIndex}`
                                                ? theme.palette.primary.darker
                                                : theme.palette.primary.dark
                                          }}
                                        >
                                          {item.menuItemTitle}
                                        </Typography>
                                      }
                                    />
                                    <Box
                                      sx={{
                                        marginLeft: 'auto',
                                        display: 'flex',
                                        alignItems: 'center',
                                        color:
                                          openSubCollapse ===
                                          `${index}-${subIndex}`
                                            ? theme.palette.primary.darker
                                            : theme.palette.primary.dark
                                      }}
                                    >
                                      {openSubCollapse ===
                                      `${index}-${subIndex}` ? (
                                        <KeyboardArrowUpIcon />
                                      ) : (
                                        <KeyboardArrowDownIcon />
                                      )}
                                    </Box>
                                  </ListItemButton>
                                </ListItem>
                                <Collapse
                                  in={
                                    openSubCollapse === `${index}-${subIndex}`
                                  }
                                  timeout="auto"
                                  unmountOnExit
                                >
                                  <List
                                    component="div"
                                    disablePadding
                                    sx={{ pl: 1 }}
                                  >
                                    {item.subMenuItems?.map(
                                      (subItem, subSubIndex) => (
                                        <ListItem
                                          key={`${index}-${subIndex}-${subSubIndex}`}
                                          disablePadding
                                          role="none"
                                        >
                                          <ListItemButton
                                            role="menuitem"
                                            aria-label={subItem.menuItemTitle}
                                            onClick={async () => {
                                              await onMenuItemClick(subItem);
                                              toggleDrawer(false)();
                                            }}
                                            sx={{
                                              '&:hover .MuiTypography-root, &:focus .MuiTypography-root, &.Mui-selected .MuiTypography-root':
                                                {
                                                  color:
                                                    theme.palette.primary.darker
                                                }
                                            }}
                                          >
                                            <ListItemText
                                              primary={
                                                <Typography
                                                  variant="subMenuText"
                                                  sx={{
                                                    color: 'primary.dark'
                                                  }}
                                                >
                                                  {subItem.menuItemTitle}
                                                </Typography>
                                              }
                                            />
                                          </ListItemButton>
                                        </ListItem>
                                      )
                                    )}
                                  </List>
                                </Collapse>
                              </React.Fragment>
                            );
                          }
                          return null;
                        })}
                    </List>
                  </Collapse>
                  <Divider />
                </React.Fragment>
              );
            }

            // --- Default rendering for other sections ---
            // const menuTitle = (
            //   <ListItem role="presentation">
            //     <ListItemText
            //       primary={
            //         sectionTitle === 'Vulnerability Scanning'
            //           ? 'Scanning Results'
            //           : sectionTitle === 'Findings Library'
            //             ? 'Inventory'
            //             : sectionTitle
            //       }
            //       slotProps={{
            //         primary: {
            //           id: `drawer-section-${index}`,
            //           sx: {
            //             fontWeight: 'bold'
            //           }
            //         }
            //       }}
            //     />
            //   </ListItem>
            // );

            const [, sectionItems] = entries[0];
            return (
              <React.Fragment key={index}>
                {sectionItems &&
                  sectionItems.length > 0 &&
                  sectionItems.map((item, subIndex) => {
                    const isHttpLink = item.path?.startsWith('http');
                    const isMailtoLink = item.path?.startsWith('mailto:');
                    const isSubMenu =
                      item.subMenuItems && item.subMenuItems.length > 0;

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
                            <ListItemText
                              primary={
                                <Typography
                                  variant="globalNav"
                                  sx={{
                                    color: 'primary.dark'
                                  }}
                                >
                                  {item.menuItemTitle}
                                </Typography>
                              }
                            />
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
                            <ListItemText
                              primary={
                                <Typography
                                  variant="globalNav"
                                  sx={{
                                    color: 'primary.dark'
                                  }}
                                >
                                  {item.menuItemTitle}
                                </Typography>
                              }
                            />
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
                            <ListItemText
                              primary={
                                <Typography
                                  variant="globalNav"
                                  sx={{
                                    color: 'primary.dark'
                                  }}
                                >
                                  {item.menuItemTitle}
                                </Typography>
                              }
                            />
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
                            <ListItemText
                              primary={
                                <Typography
                                  variant="globalNav"
                                  sx={{
                                    color: 'primary.dark'
                                  }}
                                >
                                  {item.menuItemTitle}
                                </Typography>
                              }
                            />
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
                            <ListItemText
                              primary={
                                <Typography
                                  variant="globalNav"
                                  sx={{
                                    color: 'primary.dark'
                                  }}
                                >
                                  {item.menuItemTitle}
                                </Typography>
                              }
                            />
                          </ListItemButton>
                        </ListItem>
                      );
                    }

                    // 6. Submenu
                    if (isSubMenu && onMenuItemClick) {
                      return (
                        <React.Fragment key={`${index}-${subIndex}`}>
                          <ListItem disablePadding role="none">
                            <ListItemButton
                              onClick={() => {
                                setOpenCollapse(
                                  openCollapse === `${index}-${subIndex}`
                                    ? false
                                    : `${index}-${subIndex}`
                                );
                              }}
                              role="menuitem"
                              aria-haspopup="true"
                              aria-label={item.menuItemTitle}
                            >
                              <ListItemText
                                primary={
                                  <Typography
                                    variant="globalNav"
                                    sx={{
                                      color: 'primary.dark'
                                    }}
                                  >
                                    {item.menuItemTitle}
                                  </Typography>
                                }
                              />
                              <ListItemIcon>
                                {openCollapse === `${index}-${subIndex}` ? (
                                  <KeyboardArrowUpIcon
                                    sx={{
                                      color: theme.palette.primary.dark
                                    }}
                                  />
                                ) : (
                                  <KeyboardArrowDownIcon
                                    sx={{
                                      color: theme.palette.primary.dark
                                    }}
                                  />
                                )}
                              </ListItemIcon>
                            </ListItemButton>
                          </ListItem>
                          <Collapse
                            in={openCollapse === `${index}-${subIndex}`}
                            timeout="auto"
                            unmountOnExit
                          >
                            <List component="div" sx={{ pl: 1 }}>
                              {item.subMenuItems?.map(
                                (subItem, subSubIndex) => (
                                  <ListItem
                                    key={`${index}-${subIndex}-${subSubIndex}`}
                                    disablePadding
                                    role="none"
                                  >
                                    <ListItemButton
                                      role="menuitem"
                                      aria-label={subItem.menuItemTitle}
                                      onClick={async () => {
                                        await onMenuItemClick(subItem);
                                        toggleDrawer(false)();
                                      }}
                                    >
                                      <ListItemText
                                        primary={
                                          <Typography
                                            variant="globalNav"
                                            sx={{
                                              color: 'primary.dark'
                                            }}
                                          >
                                            {subItem.menuItemTitle}
                                          </Typography>
                                        }
                                      />
                                    </ListItemButton>
                                  </ListItem>
                                )
                              )}
                            </List>
                          </Collapse>
                        </React.Fragment>
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
      ModalProps={{
        keepMounted: true
      }}
      slotProps={{
        paper: {
          sx: {
            zIndex: (theme) => theme.zIndex.modal + 1
          }
        }
      }}
    >
      {DrawerList}
    </Drawer>
  );
};
