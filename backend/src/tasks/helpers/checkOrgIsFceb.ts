import { getRepository } from 'typeorm';
import { DL_Organization, connectToDatalake2 } from '../../models';

export default async (acronym: string): Promise<boolean> => {
  // Connect to the database
  const mdl_connection = await connectToDatalake2();
  const mdl_organization_repo = mdl_connection.getRepository(DL_Organization);

  // Find the organization by acronym
  const organization = await mdl_organization_repo.findOne({
    where: { acronym },
    relations: ['sectors', 'parent']
  });

  if (!organization) {
    return false; // Return false if the organization is not found
  }

  const isOrganizationExecutive = async (
    org: DL_Organization
  ): Promise<boolean> => {
    // Check if the current organization has the EXECUTIVE sector
    if (org.sectors.some((sector) => sector.acronym === 'EXECUTIVE')) {
      return true;
    }
    // If there is a parent organization, check it recursively
    if (org.parent) {
      const parentOrg = await mdl_organization_repo.findOne({
        where: { id: org.parent.id },
        relations: ['sectors']
      });
      return parentOrg ? await isOrganizationExecutive(parentOrg) : false;
    }
    return false;
  };

  // Check if the organization or its parents are executive
  return await isOrganizationExecutive(organization);
};
