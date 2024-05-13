import { plainToClass } from 'class-transformer';
import { Host, connectToDatalake } from '../../models';

export default async (host: Host): Promise<string> => {
  console.log(`Starting to save host ${host.ipString} to datalake`);
  await connectToDatalake();
  const hostUpdatedValues = Object.keys(host)
    .map((key) => {
      if (['id'].indexOf(key) > -1) return '';
      else if (key === 'organization') return 'organizationId';
      else if (key === 'ip') return 'ipId';
      return host[key] !== null ? key : '';
    })
    .filter((key) => key !== '');
  const host_id: string = (
    await Host.createQueryBuilder()
      .insert()
      .values(host)
      .orUpdate({
        conflict_target: ['id'],
        overwrite: hostUpdatedValues
      })
      .returning('id')
      .execute()
  ).identifiers[0].id;

  return host_id;
};
