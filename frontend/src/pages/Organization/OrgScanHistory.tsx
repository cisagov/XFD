import React, { useState, useCallback } from 'react';
import { useAuthContext } from 'context';
import {
  Organization as OrganizationType,
  ScanTask,
  Scan,
  ScanSchema
} from 'types';
import { Button } from '@mui/material';
import { Column } from 'react-table';
import { Table } from 'components';
// @ts-ignore:next-line
import { formatDistanceToNow, parseISO } from 'date-fns';

interface OrganizationScan extends Partial<OrganizationType> {
  id: any;
  granularScans: any;
}

type OrgScanHistoryProps = {
  organization: OrganizationScan;
  setOrganization: Function;
  scanTasks: ScanTask[];
};

export const OrgScanHistory: React.FC<OrgScanHistoryProps> = ({
  organization,
  setOrganization,
  scanTasks
}) => {
  const { apiGet, apiPost, user, setFeedbackMessage } = useAuthContext();
  const [scans, setScans] = useState<Scan[]>([]);
  const [scanSchema, setScanSchema] = useState<ScanSchema>({});

  const dateAccessor = (date?: string) => {
    return !date || new Date(date).getTime() === new Date(0).getTime()
      ? 'None'
      : `${formatDistanceToNow(parseISO(date))} ago`;
  };

  const fetchScans = useCallback(async () => {
    try {
      const response = await apiGet<{
        scans: Scan[];
        schema: ScanSchema;
      }>('/granularScans/');
      let { scans } = response;
      const { schema } = response;

      if (user?.userType !== 'globalAdmin')
        scans = scans.filter(
          (scan) =>
            scan.name !== 'censysIpv4' && scan.name !== 'censysCertificates'
        );

      setScans(scans);
      setScanSchema(schema);
    } catch (e) {
      console.error(e);
    }
  }, [apiGet, user]);

  const updateScan = async (scan: Scan, enabled: boolean) => {
    try {
      if (!organization) return;
      await apiPost(
        `/organizations/${organization?.id}/granularScans/${scan.id}/update`,
        {
          body: {
            enabled
          }
        }
      );
      setOrganization({
        ...organization,
        granularScans: enabled
          ? organization.granularScans.concat([scan])
          : organization.granularScans.filter(
              (granularScan: { id: string }) => granularScan.id !== scan.id
            )
      });
    } catch (e: any) {
      setFeedbackMessage({
        message:
          e.status === 422 ? 'Error updating scan' : e.message ?? e.toString(),
        type: 'error'
      });
      console.error(e);
    }
  };
  const scanColumns: Column<Scan>[] = [
    {
      Header: 'Name',
      accessor: 'name',
      width: 150,
      id: 'name',
      disableFilters: true
    },
    {
      Header: 'Description',
      accessor: ({ name }) => scanSchema[name] && scanSchema[name].description,
      width: 200,
      minWidth: 200,
      id: 'description',
      disableFilters: true
    },
    {
      Header: 'Mode',
      accessor: ({ name }) =>
        scanSchema[name] && scanSchema[name].isPassive ? 'Passive' : 'Active',
      width: 150,
      minWidth: 150,
      id: 'mode',
      disableFilters: true
    },
    {
      Header: 'Action',
      id: 'action',
      maxWidth: 100,
      Cell: ({ row }: { row: { index: number } }) => {
        if (!organization) return null;
        const enabled = organization.granularScans.find(
          (scan: { id: string }) => scan.id === scans[row.index].id
        );
        return (
          <Button
            type="button"
            onClick={() => {
              updateScan(scans[row.index], !enabled);
            }}
          >
            {enabled ? 'Disable' : 'Enable'}
          </Button>
        );
      },
      disableFilters: true
    }
  ];

  const scanTaskColumns: Column<ScanTask>[] = [
    {
      Header: 'ID',
      accessor: 'id',
      disableFilters: true
    },
    {
      Header: 'Status',
      accessor: 'status',
      disableFilters: true
    },
    {
      Header: 'Type',
      accessor: 'type',
      disableFilters: true
    },
    {
      Header: 'Name',
      accessor: ({ scan }) => scan?.name,
      disableFilters: true
    },
    {
      Header: 'Created At',
      accessor: ({ createdAt }) => dateAccessor(createdAt),
      disableFilters: true,
      disableSortBy: true
    },
    {
      Header: 'Requested At',
      accessor: ({ requestedAt }) => dateAccessor(requestedAt),
      disableFilters: true,
      disableSortBy: true
    },
    {
      Header: 'Started At',
      accessor: ({ startedAt }) => dateAccessor(startedAt),
      disableFilters: true,
      disableSortBy: true
    },
    {
      Header: 'Finished At',
      accessor: ({ finishedAt }) => dateAccessor(finishedAt),
      disableFilters: true,
      disableSortBy: true
    },
    {
      Header: 'Output',
      accessor: 'output',
      disableFilters: true
    }
  ];
  return (
    <>
      <Table<Scan> columns={scanColumns} data={scans} fetchData={fetchScans} />
      <h2>Organization Scan History</h2>
      <Table<ScanTask> columns={scanTaskColumns} data={scanTasks} />
    </>
  );
};

export default OrgScanHistory;
