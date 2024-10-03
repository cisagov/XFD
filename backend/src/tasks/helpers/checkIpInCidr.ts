import { getRepository } from 'typeorm';
import { Cidr, DL_Organization, connectToDatalake2 } from '../../models';

export default async (
  ip: string,
  acronym: string
): Promise<boolean> => {
  // Connect to the database
  const mdl_connection = await connectToDatalake2();
  const mdl_organization_repo = mdl_connection.getRepository(DL_Organization);

  // Find the organization by acronym
  const organization = await mdl_organization_repo.findOne({
    where: { acronym },
    relations: ['cidrs']
  });

  if (!organization || organization.cidrs.length === 0) {
    return false; // Return false if the organization is not found or has no CIDRs
  }

  // Check if the IP is in any of the organization's CIDRs
  const mdl_cidr_repo = mdl_connection.getRepository(Cidr);
  const result = await mdl_cidr_repo
    .createQueryBuilder('cidr')
    .where('cidr.network >>= :ip', { ip })
    .andWhere('cidr.id IN (:...cidrIds)', {
      cidrIds: organization.cidrs.map((cidr) => cidr.id)
    })
    .getCount();

  return result > 0; // Return true if the IP is in any CIDR, otherwise false
};
