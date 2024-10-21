import { CommandOptions } from './ecs-client';
import checkIpInCidr from './helpers/checkIpInCidr';
import checkOrgIsFceb from './helpers/checkOrgIsFceb';
import { Organization, connectToDatabase } from '../models';

export const handler = async (commandOptions: CommandOptions) => {
  const { organizationId, organizationName } = commandOptions;
  const db_connection = await connectToDatabase();
  const organization_repo = db_connection.getRepository(Organization);

  const organizations = await organization_repo.find();

  for (const organization of organizations) {
    const current_organization = await organization_repo.findOne({
      where: { id: organization.id },
      relations: ['domains']
    });
    console.log('Running on ', organization.name);
    if (!current_organization) {
      console.log('org not found');
      continue;
    }

    const isExecutive = await checkOrgIsFceb(current_organization.acronym);

    if (isExecutive) {
      // If executive, mark all domains as isFceb = true
      for (const domain of current_organization.domains) {
        domain.isFceb = true;
        await domain.save(); // Save each domain
      }
    } else {
      for (const domain of current_organization.domains) {
        if (domain.ip) {
          // Set fromCidr field based on the check
          domain.fromCidr = await checkIpInCidr(
            domain.ip,
            current_organization.acronym
          );

          // Optionally save domain if its fromCidr value has changed
          await domain.save(); // Save the domain
        }
      }
    }
  }
};
