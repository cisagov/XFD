import { Client } from '@elastic/elasticsearch';
import { Domain, Organization } from '../models';

export const DOMAINS_INDEX = 'domains-5';
export const ORGANIZATIONS_INDEX = 'organizations-1';

interface Suggest {
  input: string | string[];
  weight: number;
}
interface DomainRecord extends Domain {
  suggest: Suggest[];
  parent_join: 'domain';
}

interface OrganizationRecord extends Organization {
  suggest: Suggest[];
}

export interface WebpageRecord {
  webpage_id: string;
  webpage_createdAt: Date | null;
  webpage_updatedAt: Date | null;
  webpage_syncedAt: Date | null;
  webpage_lastSeen: Date | null;
  webpage_url: string;
  webpage_status: string | number;
  webpage_domainId: string;
  webpage_discoveredById: string;
  webpage_responseSize: number | null;
  webpage_headers: { name: string; value: string }[];

  // Added before elasticsearch insertion (not present in the database):
  suggest?: { input: string | string[]; weight: number }[];
  parent_join?: {
    name: 'webpage';
    parent: string;
  };
  webpage_body?: string;
}

const organizationMapping = {
  name: {
    type: 'text'
  }
};

/**
 * Elasticsearch client.
 */
class ESClient {
  client: Client;

  constructor(isLocal?: boolean) {
    this.client = new Client({ node: process.env.ELASTICSEARCH_ENDPOINT! });
  }

  async syncOrganizationsIndex() {
    console.log('syncOrganizationsIndex');
    try {
      await this.client.indices.get({
        index: ORGANIZATIONS_INDEX
      });
      await this.client.indices.putMapping({
        index: ORGANIZATIONS_INDEX,
        body: { properties: organizationMapping }
      });
    } catch (e) {
      console.log('sync orgs error', e);
      await this.client.indices.create({
        index: ORGANIZATIONS_INDEX,
        body: {
          mappings: {
            properties: {
              ...organizationMapping,
              suggest: {
                type: 'completion'
              }
            },
            dynamic: true
          },
          settings: {
            number_of_shards: 2
          }
        }
      });
    }
  }

  /**
   * Creates the domains index, if it doesn't already exist.
   */
  async syncDomainsIndex() {
    console.log('syncDomainsIndex');
    const mapping = {
      services: {
        type: 'nested'
      },
      vulnerabilities: {
        type: 'nested'
      },
      webpage_body: {
        type: 'text',
        term_vector: 'yes'
      },
      parent_join: {
        type: 'join',
        relations: {
          domain: ['webpage']
        }
      }
    };
    try {
      await this.client.indices.get({
        index: DOMAINS_INDEX
      });
      await this.client.indices.putMapping({
        index: DOMAINS_INDEX,
        body: { properties: mapping }
      });
      console.log(`Index ${DOMAINS_INDEX} updated.`);
    } catch (e) {
      if (e.meta?.body?.error.type !== 'index_not_found_exception') {
        console.error(e.meta?.body);
        throw e;
      }
      await this.client.indices.create({
        index: DOMAINS_INDEX,
        body: {
          mappings: {
            properties: {
              ...mapping,
              suggest: {
                type: 'completion'
              }
            },
            dynamic: true
          },
          settings: {
            number_of_shards: 2
          }
        }
      });
      console.log(`Created index ${DOMAINS_INDEX}.`);
    }
    await this.client.indices.putSettings({
      index: DOMAINS_INDEX,
      body: {
        settings: { refresh_interval: '1800s' }
      }
    });
    console.log(`Updated settings for index ${DOMAINS_INDEX}.`);
  }

  excludeFields = (domain: Domain) => {
    const copy: any = domain;
    delete copy.ssl;
    delete copy.censysCertificatesResults;
    for (const service in copy.services) {
      delete copy.services[service].censysIpv4Results;
      delete copy.services[service].wappalyzerResults;
      delete copy.services[service].intrigueIdentResults;
    }
    return copy;
  };

  async updateOrganizations(organizations: Organization[]) {
    const organizationRecords = organizations.map((rec) => {
      return {
        suggest: [{ input: rec.name, weight: 1 }],
        ...rec
      };
    }) as OrganizationRecord[];
    const b = this.client.helpers.bulk<OrganizationRecord>({
      datasource: organizationRecords,
      onDocument(organization) {
        return [
          {
            update: {
              _index: ORGANIZATIONS_INDEX,
              _id: organization.id
            }
          },
          {
            doc_as_upsert: true
          }
        ];
      }
    });
    const result = await b;
    if (result.aborted) {
      console.error(result);
      throw new Error('Bulk operation aborted');
    }
    return result;
  }

  /**
   * Updates the given domains, upserting as necessary.
   * @param domains Domains to insert.
   */
  async updateDomains(domains: Domain[]) {
    console.log('updateDomains');
    const domainRecords = domains.map((e) => ({
      ...this.excludeFields(e),
      suggest: [{ input: e.name, weight: 1 }],
      parent_join: 'domain'
    })) as DomainRecord[];
    const b = this.client.helpers.bulk<DomainRecord>({
      datasource: domainRecords,
      onDocument(domain) {
        return [
          {
            update: {
              _index: DOMAINS_INDEX,
              _id: domain.id
            }
          },
          { doc_as_upsert: true }
        ];
      },
      onDrop(doc) {
        console.error(doc.error, doc.document);
        b.abort();
      }
    });
    const result = await b;
    if (result.aborted) {
      console.error(result);
      throw new Error('Bulk operation aborted');
    }
    return result;
  }

  /**
   * Updates the given webpages, upserting as necessary.
   * @param webpages Webpages to insert.
   */
  async updateWebpages(webpages: WebpageRecord[]) {
    console.log('updateWebpages');
    const webpageRecords = webpages.map((e) => ({
      ...e,
      suggest: [{ input: e.webpage_url, weight: 1 }],
      parent_join: {
        name: 'webpage',
        parent: e.webpage_domainId
      }
    })) as WebpageRecord[];
    const b = this.client.helpers.bulk<WebpageRecord>({
      datasource: webpageRecords,
      onDocument(webpage) {
        return [
          {
            update: {
              _index: DOMAINS_INDEX,
              _id: 'webpage_' + webpage.webpage_id,
              routing: webpage.webpage_domainId
            }
          },
          { doc_as_upsert: true }
        ];
      },
      onDrop(doc) {
        console.error(doc.error, doc.document);
        b.abort();
      }
    });
    const result = await b;
    if (result.aborted) {
      console.error(result);
      throw new Error('Bulk operation aborted');
    }
    return result;
  }

  /**
   * Searches for domains.
   * @param body Elasticsearch query body.
   */
  async searchDomains(body: any) {
    console.log('searchDomains');
    return this.client.search({
      index: DOMAINS_INDEX,
      body
    });
  }

  async searchOrganizations(body: any) {
    return this.client.search({
      index: ORGANIZATIONS_INDEX,
      body
    });
  }

  /**
   * Deletes everything in Elasticsearch
   */
  async deleteAll() {
    await this.client.indices.delete({
      index: '*'
    });
  }
}

export default ESClient;
