import React from 'react';
import { Button } from '@mui/material';
import { useAuthContext } from 'context';

export const Analytics: React.FC = () => {
    const { apiGet, apiDelete } = useAuthContext();
    let totalVisits;
    return (
        <div>
            {/* Analytics page content goes here */}
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
                <Button variant="contained" color="primary" onClick={async () => {
                    totalVisits = await apiGet('/analytics/visits-total');
                    console.log(totalVisits);
                }}>
                    Total Visits
                </Button>
            </div>
        </div>
    );
};

export default Analytics;