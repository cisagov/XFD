import React from 'react';
import { getIconType } from '../helpers/index';

// Filter the resource type and return the corresponding icon
export const IconFilter = ({ type }: { type: string }) => {
  const IconType = getIconType(type);
  return (
    <>
      <IconType />
    </>
  );
};
