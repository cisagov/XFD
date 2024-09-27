import { Organization } from './organization';
import { Scan } from './scan';

export interface Product {
  // Common name
  name: string;
  // Product name
  product?: string;
  // Product vendor
  vendor?: string;
  // Product version
  version: string;
  // Product version revision
  revision?: string;
  // CPE without version (unique identifier)
  cpe?: string;
  // Optional icon
  icon?: string;
  // Optional description
  description?: string;
  // Tags
  tags: string[];
}

export interface Service {
  port: number;
  service: string;
  id: number;
  lastSeen: string | null;
  banner: string | null;
  censysMetadata: {
    product: string;
    revision: string;
    description: string;
    version: string;
    manufacturer: string;
  } | null;
  censysIpv4Results: any;
  intrigueIdentResults: {
    fingerprint: {
      type: string;
      vendor: string;
      product: string;
      version: string;
      update: string;
      tags: string[];
      match_type: string;
      match_details: string;
      hide: boolean;
      cpe: string;
      issue?: string;
      task?: string;
      inference: boolean;
    }[];
    content: {
      type: string;
      name: string;
      hide?: boolean;
      issue?: boolean;
      task?: boolean;
      result?: boolean;
    }[];
  };
  wappalyzerResults: WappalyzerResult[];
  products: Product[];
  productSource: string | null;
  serviceSource: string | null;
}

export interface Webpage {
  id: string;
  createdAt: Date;
  updatedAt: Date;
  syncedAt: Date | null;
  domain: Domain;
  discoveredBy: Scan;
  lastSeen: Date | null;
  s3Key: string | null;
  url: string;
  status: number;
  responseSize: number | null;
}

export interface Vulnerability {
  id: string;
  domain: Domain;
  createdAt: string;
  lastSeen: string | null;
  title: string;
  cve: string | null;
  isKev?: string;
  cwe: string | null;
  cpe: string | null;
  description: string;
  cvss: number | null;
  severity: string | null;
  state: string;
  source: string;
  structuredData: { [x: string]: any };
  substate: string;
  notes: string;
  actions: {
    type: 'state-change' | 'comment';
    state?: string;
    substate?: string;
    value?: string;
    automatic: boolean;
    userId: string | null;
    userName: string | null;
    date: string;
  }[];
  references: {
    url: string;
    name: string;
    source: string;
    tags: string[];
  }[];
  service: Service;
}

export interface Domain {
  id: string;
  name: string;
  ip: string;
  createdAt: string;
  updatedAt: string;
  screenshot: string | null;
  country: string | null;
  asn: string | null;
  cloudHosted: boolean;
  services: Service[];
  vulnerabilities: Vulnerability[];
  webpages: Webpage[];
  organization: Organization;
  ssl: SSLInfo | null;
  censysCertificatesResults: any;
  fromRootDomain: string | null;
  subdomainSource: string | null;
}

export interface SSLInfo {
  issuerOrg: string | null;
  issuerCN: string | null;
  validTo: string | null;
  validFrom: string | null;
  altNames: string | null;
  protocol: string | null;
  fingerprint: string | null;
  bits: string | null;
}

export interface WappalyzerResult {
  technology?: {
    name?: string;
    categories?: number[];
    slug?: string;
    url?: string[];
    headers?: any[];
    dns?: any[];
    cookies?: any[];
    dom?: any[];
    html?: any[];
    css?: any[];
    certIssuer?: any[];
    robots?: any[];
    meta?: any[];
    scripts?: any[];
    js?: any;
    implies?: any[];
    excludes?: any[];
    icon?: string;
    website?: string;
    cpe?: string;
  };
  pattern?: {
    value?: string;
    regex?: string;
    confidence?: number;
    version?: string;
  };
  // Actual detected version
  version?: string;
}
