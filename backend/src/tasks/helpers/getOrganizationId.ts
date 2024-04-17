

import { Organization, connectToDatabase } from '../../models';

export default async (acronym: string) => {
  await connectToDatabase();

  const organization = await Organization.findOne({acronym: acronym});
  return organization!.id;
};
