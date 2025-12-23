export function capitalize(str: string | null): string | null {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export const matchPath = (paths: string[], path: string) => {
  if (paths.includes(path)) return true;
  return false;
};

export function truncateString(inputString: string) {
  // Truncate string if " (" and " at" appears
  const firstParenthesis = inputString.indexOf(' (');
  const firstAt = inputString.indexOf(' at');
  let cutOffIndex;
  if (firstParenthesis === -1 && firstAt === -1) {
    cutOffIndex = inputString.length;
  } else if (firstParenthesis === -1) {
    cutOffIndex = firstAt;
  } else if (firstAt === -1) {
    cutOffIndex = firstParenthesis;
  } else {
    cutOffIndex = Math.min(firstParenthesis, firstAt);
  }
  return inputString.substring(0, cutOffIndex);
}

export const formatNumber = (
  value: number | null | undefined
): string | null | undefined => {
  if (value == null) return null;
  if (value == undefined) return undefined;

  return new Intl.NumberFormat('en-US').format(value);
};
