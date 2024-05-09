import { plainToClass } from 'class-transformer';
import {
  VulnScan,
  DL_Organization,
  Cidr,
  Location,
  connectToDatalake
} from '../../models';

export default async (vuln_scan: VulnScan): Promise<string> => {
  console.log('Starting to save VulnScan to datalake');
  await connectToDatalake();
  const vulnScanUpdatedValues = Object.keys(vuln_scan)
    .map((key) => {
      if (['id'].indexOf(key) > -1) return '';
      else if (key === 'organization') return 'organizationId';
      else if (key === 'ip') return 'ipId';
      else if (key === 'cve') return 'cveId';
      return vuln_scan[key] !== null ? key : '';
    })
    .filter((key) => key !== '');
  const vuln_scan_id: string = (
    await VulnScan.createQueryBuilder()
      .insert()
      .values(vuln_scan)
      .orUpdate({
        conflict_target: ['id'],
        overwrite: vulnScanUpdatedValues
      })
      .returning('id')
      .execute()
  ).identifiers[0].id;

  return vuln_scan_id;
};
