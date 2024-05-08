import React from 'react';
import {
  VideoLibrary,
  Article,
  LibraryBooks,
  Handyman,
  NotificationsActive
} from '@mui/icons-material';

interface ResourceTypes {
  [key: string]: React.ElementType;
}

const resourcetypes: ResourceTypes = {
  video: VideoLibrary,
  article: Article,
  tool: Handyman,
  alerts: NotificationsActive
};

// Filter resource visibility by response
export const isResourceVisible = (response: string) => {
  const r = response.toLowerCase();
  return r === 'no' || r === 'not in scope' || r === 'not started';
};

// Filter the resource type and return the corresponding icon
export const getIconType = (type: string) => {
  const ResourceIcon = resourcetypes[type];
  return ResourceIcon ? ResourceIcon : LibraryBooks;
};
