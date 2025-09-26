import { Query, Domain, DomainSearchApiResponse } from 'types';
import { useAuthContext } from 'context';
import { useCallback } from 'react';
import { ORGANIZATION_EXCLUSIONS } from './useUserTypeFilters';

export interface DomainQuery extends Query<DomainSearchApiResponse> {
  showAll?: boolean;
}

interface ApiResponse {
  result: DomainSearchApiResponse[];
  count: number;
  url?: string;
}

const PAGE_SIZE = 15;

export const useDomainApi = (showAll?: boolean, orgId?: string) => {
  const { currentOrganization, apiPost, apiGet, user } = useAuthContext();
  const listDomains = useCallback(
    async (query: DomainQuery, doExport = false) => {
      const { page, filters, pageSize = PAGE_SIZE, order, sort } = query;
      const tableFilters: any = filters
        .filter((f) => Boolean(f.value))
        .reduce(
          (accum, next) => ({
            ...accum,
            [next.field]: next.value
          }),
          {}
        );
      const isExcludedOrg = ORGANIZATION_EXCLUSIONS.some((exc) =>
        currentOrganization?.name.toLowerCase().includes(exc)
      );

      if (
        currentOrganization &&
        !isExcludedOrg &&
        user?.user_type === 'standard'
      ) {
        tableFilters['organization'] = currentOrganization.id;
      }
      if (orgId) {
        tableFilters['organization'] = orgId;
      }

      const { result, count, url } = await apiPost<ApiResponse>(
        doExport ? '/domain/export' : '/domain/search',
        {
          body: {
            pageSize,
            page,
            filters: tableFilters,
            order,
            sort
          }
        }
      );

      return {
        domains: result,
        count,
        url,
        pageCount: Math.ceil(count / pageSize)
      };
    },
    [apiPost, currentOrganization, user, orgId]
  );

  const getDomain = useCallback(
    async (domainId: string) => {
      return await apiGet<Domain>(`/domain/${domainId}`);
    },
    [apiGet]
  );

  return {
    listDomains,
    getDomain
  };
};
