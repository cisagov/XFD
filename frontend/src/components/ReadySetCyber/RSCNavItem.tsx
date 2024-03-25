import { Divider, ListItem } from '@mui/material';
import React from 'react';

interface Props {
  name: string;
}
export const RSCNavItem: React.FC<Props> = (props) => {
  const { name } = props;
  return (
    <>
      <ListItem>{name}</ListItem>
      <Divider component="li" />
    </>
  );
};
