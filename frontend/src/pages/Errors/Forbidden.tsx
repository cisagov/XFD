import React from 'react';
import { ErrorPage } from './ErrorPage';

export const Forbidden: React.FC = () => (
  <ErrorPage
    code="403"
    title="Access denied"
    message="You do not have permission to view this page."
  />
);
