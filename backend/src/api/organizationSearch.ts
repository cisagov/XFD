import { IsArray, IsOptional, IsString, IsUUID } from 'class-validator';
import { validateBody, wrapHandler } from './helpers';
import ESClient from '../tasks/es-client';
import { Type } from 'class-transformer';

class OrganizationSearchBody {
  @IsOptional()
  @IsArray()
  @Type(() => IsUUID)
  regions?: string[];

  @IsString()
  searchTerm: string;
}

interface OrganizationSearchBodyType {
  regions?: string[];
  searchTerm: string;
}

const ALL_REGIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const buildRequest = (state: OrganizationSearchBodyType) => {
  return {
    query: {
      bool: {
        must: {
          simple_query_string: {
            fields: ['name'],
            query: state.searchTerm.length > 0 ? state.searchTerm : '*',
            default_operator: 'and'
          }
        },
        filter: [
          {
            terms: {
              regionId:
                state.regions && state.regions.length > 0
                  ? state.regions
                  : ALL_REGIONS
            }
          }
        ]
      }
    },
    _source: ['name', 'id', 'rootDomains', 'regionId']
  };
};

export const searchOrganizations = wrapHandler(async (event) => {
  const searchBody = await validateBody(OrganizationSearchBody, event.body);
  const request = buildRequest(searchBody);
  const client = new ESClient();
  let searchResults;
  try {
    searchResults = await client.searchOrganizations(request);
  } catch (e) {
    console.error(e.meta.body.error);
    throw e;
  }
  return {
    statusCode: 200,
    body: JSON.stringify(searchResults)
  };
});
