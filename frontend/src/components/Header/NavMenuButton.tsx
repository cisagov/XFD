import React from 'react';
import { NavLink, useLocation, Link as RouterLink } from 'react-router-dom';
import { Box, Button, ButtonProps, Menu, MenuItem } from '@mui/material';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';

interface MenuItemType {
  menuItemTitle: string;
  path?: string;
  users?: number;
  onClick?: () => void;
  objectStoreParams?: { bucket_name: string; object_key: string };
  subMenuItems?: MenuItemType[];
}

interface Props {
  menuItems?: MenuItemType[];
  title: string;
  onMenuItemClick?: (item: MenuItemType) => void;
}

export const NavMenuButton: React.FC<Props> = ({
  menuItems,
  title,
  onMenuItemClick
}) => {
  const location = useLocation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const menuRef = React.useRef<HTMLUListElement>(null);
  const isLink = !!menuItems?.[0]?.path || '';
  const open = Boolean(anchorEl);
  const [openSubMenuIndex, setOpenSubMenuIndex] = React.useState<number | null>(
    null
  );
  const [subAnchorEl, setSubAnchorEl] = React.useState<HTMLElement | null>(
    null
  );
  const findingsLibraryPaths = [
    '/inventory',
    '/inventory/domains',
    '/inventory/vulnerabilities'
  ];

  const isActive = isLink
    ? title === 'Findings Library'
      ? findingsLibraryPaths.includes(location.pathname)
      : menuItems?.some((item) => item.path === location.pathname)
    : open;

  const handleClick = (event: React.MouseEvent<HTMLElement>) =>
    setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);

  // Close menu on window resize
  React.useEffect(() => {
    const handleResize = () => {
      if (open) handleClose();
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [open]);

  // Close menu when route changes
  React.useEffect(() => {
    handleClose();
  }, [location.pathname]);

  // Close on Escape
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') handleClose();
    };
    if (open) document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  const id = `menu-${title.replace(/\s+/g, '-').toLowerCase()}`;

  const buttonProps: Partial<ButtonProps> & { to?: string } = {
    variant: 'globalNav',
    sx: { display: { xs: 'none', lg: 'flex' }, px: 1 },
    'aria-current': isActive ? 'page' : undefined
  };

  if (title === 'Vulnerability Scanning' || title === 'Findings Library') {
    buttonProps.component = RouterLink;
    buttonProps.to = menuItems?.[0]?.path || '';
  } else {
    buttonProps.onClick = handleClick;
    buttonProps.endIcon = open ? (
      <KeyboardArrowUpIcon />
    ) : (
      <KeyboardArrowDownIcon />
    );
    buttonProps['aria-haspopup'] = 'true';
    buttonProps['aria-expanded'] = open ? 'true' : undefined;
    buttonProps['aria-controls'] = open ? id : undefined;
    buttonProps['aria-label'] = `${title} menu`;
  }

  const borderBoxStyle = {
    display: 'flex',
    alignItems: 'center',
    borderBottom: open || isActive ? '3px solid' : '3px solid transparent',
    borderColor: open || isActive ? 'primary.dark' : 'transparent',
    borderRadius: 0
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', ml: 1 }}>
      <Button {...buttonProps}>
        <Box sx={borderBoxStyle}>{title}</Box>
      </Button>

      {menuItems && menuItems.length > 0 && (
        <>
          <Menu
            anchorEl={anchorEl}
            open={open}
            onClose={handleClose}
            id={id}
            slotProps={{ list: { 'aria-labelledby': id, ref: menuRef } }}
            disableScrollLock
          >
            {menuItems.map((item: MenuItemType, index: number) => {
              const externalLink =
                item.path?.startsWith('http') ||
                item.path?.startsWith('mailto');
              const internalLink = !!item.path && !externalLink;
              const subMenuLink = (item.subMenuItems?.length ?? 0) > 0;
              if (externalLink) {
                return (
                  <MenuItem
                    key={index}
                    component="a"
                    href={item.path}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={handleClose}
                    role="menuitem"
                  >
                    {item.menuItemTitle}
                  </MenuItem>
                );
              }

              if (internalLink) {
                return (
                  <MenuItem
                    key={index}
                    component={NavLink as React.ElementType}
                    to={item.path!}
                    onClick={handleClose}
                    role="menuitem"
                  >
                    {item.menuItemTitle}
                  </MenuItem>
                );
              }
              if (subMenuLink) {
                return (
                  <MenuItem
                    key={index}
                    onClick={(e) => {
                      setOpenSubMenuIndex(index);
                      setSubAnchorEl(e.currentTarget);
                    }}
                    role="menuitem"
                  >
                    {item.menuItemTitle}
                    <KeyboardArrowRightIcon fontSize="small" />
                  </MenuItem>
                );
              }
              return (
                <MenuItem
                  key={index}
                  onClick={() => {
                    item.onClick?.();
                    onMenuItemClick?.(item);
                    handleClose();
                  }}
                  role="menuitem"
                >
                  {item.menuItemTitle}
                </MenuItem>
              );
            })}
          </Menu>
          {subAnchorEl &&
            openSubMenuIndex !== null &&
            menuItems[openSubMenuIndex]?.subMenuItems && (
              <Menu
                anchorEl={subAnchorEl}
                open
                onClose={() => {
                  setOpenSubMenuIndex(null);
                  setSubAnchorEl(null);
                }}
                anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
                transformOrigin={{ vertical: 'top', horizontal: 'left' }}
                sx={{ mt: -1, ml: -1 }}
              >
                {menuItems[openSubMenuIndex].subMenuItems!.map(
                  (subItem, subIndex) => (
                    <MenuItem
                      key={subIndex}
                      onClick={() => {
                        subItem.onClick?.();
                        onMenuItemClick?.(subItem);
                        setOpenSubMenuIndex(null);
                        setSubAnchorEl(null);
                        handleClose();
                      }}
                      role="menuitem"
                    >
                      {subItem.menuItemTitle}
                    </MenuItem>
                  )
                )}
              </Menu>
            )}
        </>
      )}
    </Box>
  );
};
