import React from 'react';
import { useHistory } from 'react-router-dom';
import { Button, Menu, MenuItem } from '@mui/material';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';

interface LinkConfig {
  title: string | JSX.Element;
  path: string;
  onClick?: any;
}

interface Props {
  nested?: LinkConfig[];
  path?: string;
  title: string | JSX.Element;
  exact?: boolean;
  onClick?: any;
}

export const UserMenu: React.FC<Props> = (props) => {
  const { nested } = props;
  const history = useHistory();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <div>
      <Button
        startIcon={<AccountCircleIcon />}
        endIcon={<ArrowDropDownIcon />}
        style={{ color: 'white' }}
        onClick={handleClick}
      >
        My Account
      </Button>
      <Menu anchorEl={anchorEl} open={open} onClose={handleClose}>
        {nested?.map((item, index) => (
          <MenuItem key={index} onClick={() => history.push(item.path)}>
            {item.title}
          </MenuItem>
        ))}
      </Menu>
    </div>
  );
};
