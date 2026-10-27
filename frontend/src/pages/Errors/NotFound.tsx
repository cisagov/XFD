import React from 'react';
import { ErrorPage } from './ErrorPage';

export const NotFound: React.FC = () => (
  <ErrorPage
    code="404"
    title="Page not found"
    message="The page or resource you requested could not be found."
  />
);
