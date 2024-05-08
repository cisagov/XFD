import { plainToClass } from 'class-transformer';
import { DL_Cve, connectToDatalake } from '../../models';

export default async (cveObj: DL_Cve): Promise<string | null> => {
  console.log('Starting to save CVE to datalake');
  await connectToDatalake();
  const cveUpdatedValues = Object.keys(cveObj)
    .map((key) => {
      if (['name'].indexOf(key) > -1) return '';
      return cveObj[key] != null ? key : '';
    })
    .filter((key) => key !== '');

  let queryBuilder = DL_Cve.createQueryBuilder().insert().values(cveObj);

  if (cveUpdatedValues.length > 0) {
    queryBuilder = queryBuilder.orUpdate({
      conflict_target: ['name'],
      overwrite: cveUpdatedValues
    });
  } else {
    queryBuilder = queryBuilder.orIgnore();
  }

  let cve_id: string | null;

  if (cveUpdatedValues.length > 0) {
    cve_id = (await queryBuilder.returning('id').execute()).identifiers[0].id;
  } else {
    await queryBuilder.execute();
    const cve_promise = await DL_Cve.findOne({ where: { name: cveObj.name } });
    console.log(cve_promise);
    cve_id = cve_promise ? cve_promise.id : null;
  }
  return cve_id;
};
