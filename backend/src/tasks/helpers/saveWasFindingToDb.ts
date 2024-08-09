import { plainToClass } from 'class-transformer';
import { WasFinding, connectToDatalake2 } from '../../models';

export default async (wasFindingObj: WasFinding): Promise<string | null> => {
  console.log(
    `Starting to save WAS finding to datalake: ${wasFindingObj.name}`
  );

  const datalakeConnnection = await connectToDatalake2();
  const dl_was_finding = datalakeConnnection.getRepository(WasFinding);
  const wasFindingValues = Object.keys(wasFindingObj)
    .map((key) => {
      if (['id'].indexOf(key) > -1) return '';
      else if (key === 'organization') return 'organizationId';
      return wasFindingObj[key] != null ? key : '';
    })
    .filter((key) => key !== '');
  console.log(wasFindingObj);
  const was_finding_id: string = (
    await dl_was_finding
      .createQueryBuilder()
      .insert()
      .values(wasFindingObj)
      .orUpdate({
        conflict_target: ['id'],
        overwrite: wasFindingValues
      })
      .returning('id')
      .execute()
  ).identifiers[0].id;

  return was_finding_id;
};
