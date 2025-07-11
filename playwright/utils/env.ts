// utils/env.ts
export function determineUrl(): string {
  return process.env.PW_XFD_URL || 'http://localhost';
}

export function determineHeadless(): boolean {
  if (process.env.PW_HEADLESS) {
    return process.env.PW_HEADLESS !== 'false';
  }
  const url = determineUrl();
  return !url.includes('localhost');
}
