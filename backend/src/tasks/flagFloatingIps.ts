import { CommandOptions } from './ecs-client';
import checkIpInCidr from './helpers/checkIpInCidr';
import checkOrgIsFceb from './helpers/checkOrgIsFceb';
import { Organization, connectToDatabase } from '../models';

export const handler = async (commandOptions: CommandOptions) => {
  const { organizationId, organizationName } = commandOptions;
  const db_connection = await connectToDatabase();
  const organization_repo = db_connection.getRepository(Organization);

  const organizations = await organization_repo.find({
    where: {id: organizationId},
    relations: ['domains']
  });


  for (const organization of organizations) {
    console.log('Running on ', organizationName)
    const isExecutive = await checkOrgIsFceb(organization.acronym);

    if (isExecutive) {
      // If executive, mark all domains as isFceb = true
      for (const domain of organization.domains) {
        domain.isFceb = true;
        await domain.save(); // Save each domain
      }
    }
    else{
      for (const domain of organization.domains) {
        if (domain.ip) {
          // Set fromCidr field based on the check
          domain.fromCidr = await checkIpInCidr(domain.ip, organization.acronym);;
    
          // Optionally save domain if its fromCidr value has changed
          await domain.save(); // Save the domain
        }
      }
    }
  }
};
