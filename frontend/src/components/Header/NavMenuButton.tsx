import React from 'react';
import { NavLink, useLocation, Link as RouterLink } from 'react-router-dom';
import { Box, Button, ButtonProps, Menu, MenuItem } from '@mui/material';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';

interface MenuItemType {
  menuItemTitle: string;
  path: string;
  users?: number;
  onClick?: () => void;
}

interface Props {
  menuItems?: MenuItemType[];
  title: string;
  path?: string;
}

export const NavMenuButton: React.FC<Props> = ({ menuItems, title, path }) => {
  const location = useLocation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const menuRef = React.useRef<HTMLUListElement>(null);
  const isLink = !!path;
  const open = Boolean(anchorEl);

  const isActive = isLink ? location.pathname === path : open;

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

  const isDropdown = !isLink && menuItems && menuItems.length > 0;

  const buttonProps: Partial<ButtonProps> & { to?: string } = {
    variant: 'text',
    sx: {
      display: { xs: 'none', lg: 'flex' },
      whiteSpace: 'nowrap',
      borderRadius: 0
    },
    'aria-current': isActive ? 'page' : undefined
  };

  if (isLink) {
    buttonProps.component = RouterLink;
    buttonProps.to = path!;
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
    borderBottom: isDropdown
      ? open
        ? '3px solid'
        : '3px solid transparent'
      : isActive
        ? '3px solid'
        : '3px solid transparent',
    borderColor: isDropdown
      ? open
        ? 'primary.dark'
        : 'transparent'
      : isActive
        ? 'primary.dark'
        : 'transparent',
    borderRadius: 0
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center' }}>
      <Box sx={{ display: { xs: 'none', lg: 'flex' } }}>
        <Button {...buttonProps}>
          <Box sx={borderBoxStyle}>{title}</Box>
        </Button>
      </Box>
      {menuItems && menuItems.length > 0 && (
        <Menu
          anchorEl={anchorEl}
          open={open}
          onClose={handleClose}
          id={id}
          MenuListProps={{
            'aria-labelledby': id,
            role: 'menu',
            ref: menuRef
          }}
        >
          {menuItems.map((item, index) => (
            <MenuItem
              key={index}
              component={NavLink}
              to={item.onClick ? '#' : item.path}
              selected={item.path === location.pathname && !item.onClick}
              onClick={() => item.onClick?.()}
              tabIndex={0}
              role="menuitem"
            >
              {item.menuItemTitle}
            </MenuItem>
          ))}
        </Menu>
      )}
    </Box>
  );
};
