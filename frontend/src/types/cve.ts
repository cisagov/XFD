import { Cpe } from './cpe';
export interface Cve {
  id: string;
  name: string | null;
  description: string | null;
  modifiedAt: Date;
  publishedAt: Date;
  status: string | null;
  cvssV2Source: string | null;
  cvssV2Type: string | null;
  cvssV2Version: string | null;
  cvssV2VectorString: string | null;
  cvssV2BaseScore: string | null;
  cvssV2BaseSeverity: string | null;
  cvssV2ExploitabilityScore: string | null;
  cvssV2ImpactScore: string | null;
  cvssV3Source: string | null;
  cvssV3Type: string | null;
  cvssV3Version: string | null;
  cvssV3VectorString: string | null;
  cvssV3BaseScore: string | null;
  cvssV3BaseSeverity: string | null;
  cvssV3ExploitabilityScore: string | null;
  cvssV3ImpactScore: string | null;
  cvssV4Source: string | null;
  cvssV4Type: string | null;
  cvssV4Version: string | null;
  cvssV4VectorString: string | null;
  cvssV4BaseScore: string | null;
  cvssV4BaseSeverity: string | null;
  cvssV4ExploitabilityScore: string | null;
  cvssV4ImpactScore: string | null;
  references: string[] | null;
  weaknesses: string[] | null;
  cpes: Cpe[];
}
