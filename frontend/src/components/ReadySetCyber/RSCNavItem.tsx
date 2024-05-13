import React from 'react';
import { ListItemButton } from '@mui/material';
import { HashLink } from 'react-router-hash-link';

interface Props {
  name: string;
}
export const RSCNavItem: React.FC<Props> = (props) => {
  const { name } = props;

  return (
    <HashLink
      style={{
        textDecoration: 'none',
        color: 'black'
      }}
      to={`#${name}`}
    >
      <ListItemButton divider>{name}</ListItemButton>
    </HashLink>
  );
};
