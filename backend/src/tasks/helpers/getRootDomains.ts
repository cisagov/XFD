import { Organization, connectToDatabase } from '../../models';

export default async (organizationId: string) => {
  await connectToDatabase();

  const organization = await Organization.findOneBy({ id: organizationId });
  return organization!.rootDomains;
};
