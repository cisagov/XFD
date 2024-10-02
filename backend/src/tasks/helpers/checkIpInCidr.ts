import { getRepository } from 'typeorm';
import { Cidr, DL_Organization, connectToDatalake2 } from '../../models';

export default async (
  ip: string,
  acronym: string
): Promise<{ isInCidr: boolean; isExecutive: boolean }> => {
  // await connectToDatalake2()
  // const cidrRepository = getRepository(Cidr);
  // const organizationRepository = getRepository(DL_Organization);

  // Find the organization by acronym
  const mdl_connection = await connectToDatalake2();
  const mdl_organization_repo = mdl_connection.getRepository(DL_Organization);
  const organization = await mdl_organization_repo.findOne({
    where: { acronym },
    relations: ['cidrs', 'sectors', 'parent']
  });

  if (!organization) {
    return { isInCidr: false, isExecutive: false };
  }

  const isOrganizationExecutive = async (
    org: DL_Organization
  ): Promise<boolean> => {
    if (org.sectors.some((sector) => sector.acronym === 'EXECUTIVE')) {
      return true;
    }
    if (org.parent) {
      const parentOrg = await mdl_organization_repo.findOne({
        where: { id: org.parent.id },
        relations: ['sectors']
      });

      return parentOrg ? await isOrganizationExecutive(parentOrg) : false;
    }
    return false;
  };

  const isExecutive = await isOrganizationExecutive(organization);

  // Get CIDRs related to the organization
  const cidrs = organization.cidrs.map((cidr) => cidr.network);

  if (cidrs.length === 0) {
    return { isInCidr: false, isExecutive }; // No CIDRs associated with the organization
  }

  // Check if the IP is in any of the CIDRs
  const mdl_cidr_repo = mdl_connection.getRepository(Cidr);
  const result = await mdl_cidr_repo
    .createQueryBuilder('cidr')
    .where('cidr.network >>= :ip', { ip })
    .andWhere('cidr.id IN (:...cidrIds)', {
      cidrIds: organization.cidrs.map((cidr) => cidr.id)
    })
    .getCount();

  return { isInCidr: result > 0, isExecutive };
};
