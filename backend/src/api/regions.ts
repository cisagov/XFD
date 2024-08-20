import { connectToDatabase, Organization } from '../models';
import { wrapHandler } from './helpers';
import { getManager } from 'typeorm';

export const getAll = wrapHandler(async (event) => {
  await connectToDatabase();

  const entityManager = getManager();

  const regions = await entityManager.query(
    `SELECT DISTINCT organization."regionId"
      FROM organization
      WHERE organization."regionId" IS NOT NULL;`
  );

  return {
    statusCode: 200,
    body: JSON.stringify(regions)
  };
});
