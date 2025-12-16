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
  is_kev?: boolean | null;
  is_kev_ransomware?: boolean | null;
  cpe?: string | null;
  substate?: string | null;
  [k: string]: any;
};

export const makeVuln = (i = 1, overrides: Partial<Vuln> = {}): Vuln => {
  const idx = i;
  // Generate dates dynamically: 43 days ago + idx seconds for uniqueness
  // This ensures tests remain stable regardless of when they run
  const baseDate = new Date(Date.now() - (43 * 24 * 60 * 60 * 1000) + (idx * 1000));
  return {
    id: `vuln-${idx}`,
    scan_source: 'vuln_scanning_tickets',
    created_at: baseDate.toISOString(),
    updated_at: baseDate.toISOString(),
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

  // ensure unique titles: if duplicates occur, append the 1-based index
  const seen = new Map<string, number>();
  for (let i = 0; i < items.length; i++) {
    const title = items[i].title ?? '';
    if (seen.has(title)) {
      const countSeen = seen.get(title)! + 1;
      seen.set(title, countSeen);
      // preserve original title but add suffix so tests can target unique strings
      items[i].title = `${title} ${i + 1}`;
    } else {
      seen.set(title, 1);
    }
  }

  return { result: items, count: items.length };
};
