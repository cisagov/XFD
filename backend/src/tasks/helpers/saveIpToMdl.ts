import { plainToClass } from 'class-transformer';
import { Ip, connectToDatalake } from '../../models';

export default async (ipObj: Ip): Promise<string | null> => {
  console.log(`Starting to save IP to datalake: ${ipObj.ip}`);
  await connectToDatalake();
  const ipUpdatedValues = Object.keys(ipObj)
    .map((key) => {
      if (['ip', 'organization'].indexOf(key) > -1) return '';
      return ipObj[key] != null ? key : '';
    })
    .filter((key) => key !== '');

  let queryBuilder = Ip.createQueryBuilder().insert().values(ipObj);

  if (ipUpdatedValues.length > 0) {
    queryBuilder = queryBuilder.orUpdate({
      conflict_target: ['ip', 'organization'],
      overwrite: ipUpdatedValues
    });
  } else {
    queryBuilder = queryBuilder.orIgnore();
  }

  let ip_id: string | null;

  if (ipUpdatedValues.length > 0) {
    ip_id = (await queryBuilder.returning('id').execute()).identifiers[0].id;
  } else {
    await queryBuilder.execute();
    const ip_promise = await Ip.findOne({
      where: { ip: ipObj.ip, organization: ipObj.organization }
    });
    console.log(ip_promise);
    ip_id = ip_promise ? ip_promise.id : null;
  }

  return ip_id;
};
