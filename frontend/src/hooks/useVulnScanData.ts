import { useState, useEffect } from 'react';
import { VulnScanDataTransformed } from 'types/vuln-scan-stats';
import { transformVulnScanData } from 'utils/transformVulnScanData';
import { useAuthContext } from 'context';
import { ENDPOINTS } from '@/constants/endpoints';
import { InitialVSData } from '@/constants/vsdashdata';
import { NO_DATA_FALLBACK_LABEL } from '@/constants/vsdashdata';

export function useVulnScanData(orgId: string) {
  const { apiPost } = useAuthContext();
  const [data, setData] = useState<VulnScanDataTransformed>(InitialVSData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orgId) {
      setError(
        "Please join an organization to be shown your organization's vulnerability scan data."
      );
      setData(InitialVSData);
      return;
    }
    const fetchVSScan = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiPost(ENDPOINTS.STATS_TRENDS, {
          body: {
            filters: {
              organization_id: orgId,
              sources: ['vs', 'port', 'port_service', 'host'],
              enhanced_data: false
            }
          }
        });

        const isEmpty =
          !response?.host_summaries?.length &&
          !response?.port_scan_summaries?.length &&
          !response?.port_scan_service_summaries?.length &&
          !response?.vuln_scan_summaries?.length;

        if (!response || isEmpty) {
          setData(InitialVSData);
          setError(
            'No recent scan data was found for the selected organization.'
          );
          return;
        }

        const transformed = transformVulnScanData(response);

        const vsLabel = transformed.vulnScanSummary[0]?.vulnerabilityScan;
        if (vsLabel === NO_DATA_FALLBACK_LABEL) {
          setData(InitialVSData);
          setError('NO_DATA');
          return;
        }

        setData(transformed);
      } catch (err: any) {
        console.error(err);
        setError(
          err.message +
            '. Failed to load vulnerability scan data. See the console log for more details.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchVSScan();
  }, [apiPost, orgId]);

  return { data, loading, error };
}
