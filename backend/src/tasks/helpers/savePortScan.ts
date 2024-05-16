import { plainToClass } from 'class-transformer';
import { PortScan, connectToDatalake } from '../../models';

export default async (port_scan: PortScan): Promise<string> => {
  console.log(
    `Starting to save port scan ${port_scan.ipString} ${port_scan.port} to datalake`
  );
  await connectToDatalake();
  const portScanUpdatedValues = Object.keys(port_scan)
    .map((key) => {
      if (['id'].indexOf(key) > -1) return '';
      else if (key === 'organization') return 'organizationId';
      else if (key === 'ip') return 'ipId';
      return port_scan[key] !== null ? key : '';
    })
    .filter((key) => key !== '');
  const port_scan_id: string = (
    await PortScan.createQueryBuilder()
      .insert()
      .values(port_scan)
      .orUpdate({
        conflict_target: ['id'],
        overwrite: portScanUpdatedValues
      })
      .returning('id')
      .execute()
  ).identifiers[0].id;

  return port_scan_id;
};
