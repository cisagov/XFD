import React from 'react';
import Button from '@mui/material/Button';
import { FileDownload } from '@mui/icons-material';
import Tooltip from '@mui/material/Tooltip';
import { useAuthContext } from 'context';

export const ExportCustomerMetricsButton: React.FC = () => {
  const { apiGet, user } = useAuthContext();
  const [loading, setLoading] = React.useState(false);

  if (user?.user_type !== 'globalAdmin') {
    return null;
  }

  const parseFilename = (
    contentDispositionHeader: string | null
  ): string | null => {
    if (!contentDispositionHeader) return null;
    const m = /filename\s*=\s*"([^"]+)"/i.exec(contentDispositionHeader);
    return m ? m[1] : null;
  };

  const handleDownload = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res: any = await apiGet('/metrics/customers', {
        response: true,
        responseType: 'blob',
        headers: { Accept: 'text/csv' },
        withCredentials: true
      });

      // Extract filename from Content-Disposition header or use default
      const filename =
        parseFilename(res?.headers?.['content-disposition']) ||
        'customer-metrics.csv';
      if (
        filename === 'customer-metrics.csv' &&
        process.env.NODE_ENV !== 'production'
      ) {
        console.warn(
          '[ExportCustomerMetrics] Unable to parse filename from Content-Disposition header, using default filename'
        );
      }

      const blob: Blob =
        res?.data instanceof Blob
          ? res.data
          : new Blob([res?.data ?? ''], { type: 'text/csv; charset=utf-8' });

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      console.error('Failed to download Customer Metrics CSV:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Tooltip
      title="Download most recent daily user and organization metrics in CSV format."
      placement="top"
    >
      <span>
        <Button
          variant="contained"
          onClick={handleDownload}
          disabled={loading}
          startIcon={loading ? undefined : <FileDownload />}
          aria-label="Download most recent daily user and organization metrics in CSV format."
          sx={{
            backgroundColor: 'rgb(0, 94, 162)',
            color: '#fff',
            fontFamily: 'Helvetica, Arial, sans-serif',
            textTransform: 'none',
            fontWeight: 600,
            '&:hover': { backgroundColor: 'rgb(0, 84, 146)' },
            '&:disabled': {
              backgroundColor: 'rgba(0, 94, 162, 0.5)',
              color: '#fff'
            }
          }}
        >
          Download Customer Metrics
        </Button>
      </span>
    </Tooltip>
  );
};
