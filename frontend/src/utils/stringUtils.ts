export function capitalize(str: string | null): string | null {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}
