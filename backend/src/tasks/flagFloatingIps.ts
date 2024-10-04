import { CommandOptions } from './ecs-client';
import checkIpInCidr from './helpers/checkIpInCidr';
import { Organization, connectToDatabase } from '../models';

export const handler = async (commandOptions: CommandOptions) => {
  const db_connection = await connectToDatabase();
  const organization_repo = db_connection.getRepository(Organization);
  const organizations = await organization_repo.find({
    relations: ['domains']
  });
  for (const organization of organizations) {
    for (const domain of organization.domains) {
      if (domain.ip) {
        const cidrSectorDict = await checkIpInCidr(
          domain.ip,
          organization.acronym
        );
        if (cidrSectorDict['isInCidr']) {
          domain.fromCidr = true;
        }
        if (cidrSectorDict['isExecutive']) {
          domain.isFceb = true;
        }
        domain.save();
      }
    }
  }
};
