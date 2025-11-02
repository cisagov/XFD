import { Role } from './role';
import { ScanTask } from './scan-task';
import { Scan } from './scan';

export interface Organization {
  id: string;
  name: string;
  root_domains: string[];
  ip_blocks: string[];
  user_roles?: Role[];
  scan_tasks?: ScanTask[];
  is_passive: boolean;
  granular_scans?: Scan[];
  tags?: OrganizationTag[];
  parent?: Organization | null;
  children?: Organization[];
  pending_domains: PendingDomain[] | string[] | null;
  created_at?: string | null;
  updated_at?: string | null;
  country?: string;
  region_id?: string;
  state?: string;
  state_fips?: number;
  state_name?: string;
  county?: string;
  county_fips?: number;
  acronym: string;
  type: string;
  user_count?: number;
  tag_names?: string[];
}

export interface UserOrganization {
  id: string;
  name: string;
  tags: OrganizationTag[];
  country?: string;
  region_id?: string;
  state?: string;
  state_fips?: number;
  state_name?: string;
  county?: string;
  county_fips?: number;
  acronym?: string;
  type?: string;
  user_count?: number;
  tag_names?: string[];
}

export interface PendingDomain {
  name: string;
  token: string;
}

export interface OrganizationTag {
  id: string;
  name: string;
  tags: OrganizationTag[];
  organizations: Organization[];
  scans: Scan[];
}
