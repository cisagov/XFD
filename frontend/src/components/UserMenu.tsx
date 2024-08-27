import React from 'react';
import { useHistory } from 'react-router-dom';
import { Box, Button, Menu, MenuItem } from '@mui/material';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import { useAuthContext } from 'context';

interface MenuItemType {
  title: string;
  path: string;
  users?: number;
  exact: boolean;
  onClick?: any;
}

interface Props {
  userMenuItems: MenuItemType[];
}

export const UserMenu: React.FC<Props> = (props) => {
  const { userMenuItems } = props;
  const { user } = useAuthContext();
  const history = useHistory();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const handleNavigate = (path: string) => {
    handleClose();
    history.push(path);
  };
  const filteredMenuItems = userMenuItems.filter((item) => {
    const userType = user?.userType;
    const userAccessLevel = item.users ?? 0;
    return (
      userType === 'globalAdmin' ||
      ((userType === 'regionalAdmin' || userType === 'globalView') &&
        userAccessLevel <= 2) ||
      userAccessLevel <= 1
    );
  });
  return (
    <Box ml={2}>
      <Button
        startIcon={<AccountCircleIcon />}
        endIcon={<ArrowDropDownIcon />}
        style={{ color: 'white' }}
        onClick={handleClick}
      >
        My Account
      </Button>
      <Menu anchorEl={anchorEl} open={open} onClose={handleClose}>
        {filteredMenuItems.map((item, index) => (
          <MenuItem
            key={index}
            onClick={
              item.onClick ? item.onClick : () => handleNavigate(item.path)
            }
          >
            {item.title}
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
};
