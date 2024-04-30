import { connectToDatabase, Domain } from '../models';
import { spawnSync } from 'child_process';
import { readFileSync } from 'fs';
import { CommandOptions } from './ecs-client';
import getRootDomains from './helpers/getRootDomains';
import * as path from 'path';
import { DataSource, DeepPartial } from 'typeorm';

const OUT_PATH = path.join(__dirname, 'out-' + Math.random() + '.txt');
let connection: DataSource;
export const handler = async (commandOptions: CommandOptions) => {
  const { organizationId, organizationName, scanId } = commandOptions;

  console.log('Running findomain on organization', organizationName);
  connection = await connectToDatabase();
  const rootDomains = await getRootDomains(organizationId!);

  for (const rootDomain of rootDomains) {
    try {
      const args = [
        '--exclude-sources',
        'spyse',
        '-it',
        rootDomain,
        '-u',
        OUT_PATH
      ];
      console.log('Running findomain with args', args);
      spawnSync('findomain', args, { stdio: 'pipe' });
      const output = String(readFileSync(OUT_PATH));
      const lines = output.split('\n');
      const domains: Domain[] = [];
      for (const line of lines) {
        if (line == '') continue;
        const split = line.split(',');
        domains.push(
          Domain.create({
            name: split[0],
            ip: split[1],
            organization: { id: organizationId },
            fromRootDomain: rootDomain,
            subdomainSource: 'findomain',
            discoveredBy: { id: scanId }
          })
        );
      }
      await saveOrUpdateDomains(domains);
      console.log(`Findomain created/updated ${domains.length} new domains`);
    } catch (e) {
      console.error(e);
    }
  }
};

async function saveOrUpdateDomains(domains: Domain[]) {
  console.log('Saving or updating domains', domains);
  await connection.transaction(async (entityManager) => {
    for (const domain of domains) {
      let existingDomain = await entityManager.findOneBy(Domain, {
        name: domain.name,
        organization: { id: domain.organization.id }
      });
      if (existingDomain) {
        // If domain exists, retrieve its values for 'fromRootDomain' and 'discoveredBy'
        const preservedData: DeepPartial<Domain> = {
          fromRootDomain: existingDomain.fromRootDomain,
          discoveredBy: existingDomain.discoveredBy
        };
        // Modify domain object to use values from existingDomain for 'discoveredBy' and 'fromRootDomain'
        const { fromRootDomain, discoveredBy, ...updateData } = domain;
        entityManager.merge(Domain, existingDomain, updateData, preservedData);
      } else {
        // Else create new domain
        existingDomain = entityManager.create(Domain, domain);
      }
      await entityManager.save(existingDomain);
    }
  });
}
