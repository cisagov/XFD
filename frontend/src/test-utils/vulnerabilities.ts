export type Vuln = {
  id: string;
  scan_source?: string;
  created_at?: string;
  updated_at?: string;
  cve?: string | null;
  title: string;
  product?: string | null;
  domain_string?: string;
  domain?: { id: string; name: string };
  protocol?: string | null;
  port?: string | null;
  cvss?: number | null;
  severity?: string | null;
  state?: string | null;
  is_kev?: boolean;
  is_kev_ransomware?: boolean;
  cpe?: string | null;
  substate?: string | null;
  [k: string]: any;
};

export const makeVuln = (i = 0, overrides: Partial<Vuln> = {}): Vuln => {
  const idx = i;
  return {
    id: `vuln-${idx}`,
    scan_source: 'vuln_scanning_tickets',
    created_at: new Date(2025, 9, 27, 15, 59, idx).toISOString(),
    updated_at: new Date(2025, 9, 27, 15, 59, idx).toISOString(),
    cve: `CVE-2025-0${idx}`,
    title: overrides.title ?? `CVE-2013-4041 Sample Vuln ${idx}`,
    product: 'cpe:/a:microsoft:iis',
    domain_string: `192.0.2.${idx}`,
    domain: { id: `domain-${idx}`, name: `192.0.2.${idx}` },
    protocol: 'tcp',
    port: '80',
    cvss: 5.0,
    severity: 'Medium',
    state: 'open',
    is_kev: false,
    is_kev_ransomware: false,
    cpe: 'cpe:/a:microsoft:iis',
    substate: 'unconfirmed',
    ...overrides
  };
};

export const makeVulnResponse = (
  count = 2,
  perItemOverride?: (index: number) => Partial<Vuln>
) => {
  const items: Vuln[] = Array.from({ length: count }).map((_, idx) =>
    makeVuln(idx + 1, perItemOverride?.(idx) ?? {})
  );
  return { result: items, count: items.length };
};
