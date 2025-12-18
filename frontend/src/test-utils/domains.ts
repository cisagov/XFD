export type Domain = {
  id: string;
  name: string;
  created_at?: string;
  updated_at?: string;
  organization_id?: string;
  [k: string]: any;
};

export const makeDomain = (i = 1, overrides: Partial<Domain> = {}): Domain => {
  const idx = i;
  return {
    id: `domain-${idx}`,
    organization: { id: `org-${idx}`, name: `Organization ${idx}` },
    name: `192.0.2.${idx}`,
    ip: `192.0.2.${idx}`,
    ports_preview: '80/tcp, 443/tcp',
    services_preview: 'http, https',
    services_count: 2,
    vulnerabilities_count: 5,
    created_at: new Date(2025, 9, 27, 15, 59, idx).toISOString(),
    updated_at: new Date(2025, 9, 27, 15, 59, idx).toISOString(),
    ...overrides
  };
};

export const makeDomainResponse = (
  count = 2,
  perItemOverride?: (index: number) => Partial<Domain>
) => {
  const items: Domain[] = Array.from({ length: count }).map((_, idx) =>
    makeDomain(idx + 1, perItemOverride?.(idx) ?? {})
  );
  return { result: items, count: items.length };
};
