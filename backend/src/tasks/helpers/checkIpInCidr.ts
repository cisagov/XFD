import { getRepository } from 'typeorm';
import { Cidr, DL_Organization,connectToDatalake } from '../../models';

export default async (ip: string, acronym: string): Promise<{ isInCidr: boolean; isExecutive: boolean }> => {
    await connectToDatalake()
    // const cidrRepository = getRepository(Cidr);
    // const organizationRepository = getRepository(DL_Organization);

    // Find the organization by acronym
    const organization = await DL_Organization.findOne({
        where: { acronym },
        relations: ['cidrs','sectors'],
    });

    if (!organization) {
        throw new Error(`Organization with acronym ${acronym} not found.`);
    }

    const isExecutive = organization.sectors.some(sector => sector.acronym === 'EXECUTIVE');

    // Get CIDRs related to the organization
    const cidrs = organization.cidrs.map(cidr => cidr.network);

    if (cidrs.length === 0) {
        return { isInCidr: false, isExecutive }; // No CIDRs associated with the organization
    }

    // Check if the IP is in any of the CIDRs
    const result = await Cidr
        .createQueryBuilder('cidr')
        .where('cidr.cidr >>= :ip', { ip })
        .andWhere('cidr.id IN (:...cidrIds)', { cidrIds: organization.cidrs.map(cidr => cidr.id) })
        .getCount();

        
    return { isInCidr: result > 0, isExecutive };
}