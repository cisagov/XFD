export interface ContextType {
  addFilter(name: string, value: any, filterType: 'all' | 'any' | 'none'): void;
  clearFilters: any;
  saveSearch: any;
  removeFilter(
    name: string,
    value: any,
    filterType: 'all' | 'any' | 'none'
  ): void;
  setSearchTerm(s: string, opts?: any): void;
  autocompletedResults: any[];
  autocompletedResultsRequestId: string;
  autocompletedSuggestions: any;
  current: number;
  error: string;
  facets: any;
  filters: any[];
  isLoading: boolean;
  pagingEnd: number;
  pagingStart: number;
  requestId: string;
  reset(): void;
  resultSearchTerm: string;
  results: Result[];
  resultsPerPage: number;
  searchTerm: string;
  setCurrent(current: number): void;
  setFilter(): void;
  setResultsPerPage(): void;
  setSort(field: string, direction: 'asc' | 'desc'): void;
  sort_direction: '' | 'asc' | 'desc';
  setResultsPerPage(count: number): void;
  sort_field: string;
  totalPages: number;
  totalResults: number;
  wasSearched: boolean;
  noResults: boolean;
}

export interface Result {
  asn: { raw: any };
  cloud_hosted: { raw?: boolean };
  country: { raw: any };
  created_at: { raw: string };
  from_root_domain: { raw: string };
  id: { raw: string };
  ip: { raw: string };
  name: { raw: string };
  organization: {
    raw: {
      created_at: string;
      id: string;
      ip_blocks: any[];
      is_passive: boolean;
      name: string;
      root_domains: string[];
      updated_at: string;
    };
  };
  reverse_name: { raw: string };
  screenshot: { raw: string };
  services: { raw: any[] };
  ssl: { raw: any };
  suggest: { raw: any[] };
  synced_at: { raw: string };
  updated_at: { raw: string };
  vulnerabilities: { raw: any[] };
}
