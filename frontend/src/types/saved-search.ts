import { User } from './user';
// import { Vulnerability } from './vulnerability';

export interface SavedSearch {
  id: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  searchTerm: string;
  count: number;
  filters: { field: string; values: any[]; type: string }[];
  createdBy: User;
  searchPath: string;
  sortField: string;
  sortDirection: string;
  // The following properties are deprecated due to the refactor of the Save Search Modal.
  // The Create Vulnerabilities functionality has been removed as it is no longer needed.
  // These properties are kept here for reference and will be removed in future versions.
  // createVulnerabilities: boolean;
  // vulnerabilityTemplate: Partial<Vulnerability>;
}
