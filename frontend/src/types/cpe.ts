import { Cve } from './cve';
export interface Cpe {
  id: string;
  name: string;
  last_seen_at: Date;
  vendor?: string | any;
  version: string;
  cves: Cve[];
}
