import React from 'react';
import { useAuthContext } from 'context';

export const Analytics: React.FC = () => {

const { user, apiGet, apiPost } = useAuthContext();
    
  return (
    <div>
      <h1>Analytics</h1>
      <p>This is the Analytics page.</p>
    </div>
  );
}
export default Analytics;