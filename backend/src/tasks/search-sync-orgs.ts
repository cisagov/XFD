import {
  Domain,
  connectToDatabase,
  Vulnerability,
  Webpage,
  Organization
} from '../models';
import { CommandOptions } from './ecs-client';
import { In } from 'typeorm';
import ESClient from './es-client';
import { chunk } from 'lodash';
import pRetry from 'p-retry';

/**
 * Chunk sizes. These values are small during testing to facilitate testing.
 */
export const DOMAIN_CHUNK_SIZE = typeof jest === 'undefined' ? 50 : 10;
export const ORGANIZATION_CHUNK_SIZE = typeof jest === 'undefined' ? 50 : 10;

export const handler = async () => {
  const client = new ESClient();
  const orgQs = Organization.createQueryBuilder('organization');
  const orgIds = (await orgQs.getMany()).map((e) => e.id);
  console.log(`Got ${orgIds.length} organizations.`);
  if (orgIds.length) {
    const organizationIdChunks = chunk(orgIds, ORGANIZATION_CHUNK_SIZE);
    for (const organizationIdChunk of organizationIdChunks) {
      const organizations = await Organization.find({
        where: { id: In(organizationIdChunk) }
      });
      console.log(`Syncing ${organizations.length} organizations...`);
      await pRetry(() => client.updateOrganizations(organizations), {
        retries: 3,
        randomize: true
      });
      // Need to add a synced_at field to organizations
    }
  }
};
