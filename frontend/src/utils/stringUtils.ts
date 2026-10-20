import { STATE_ABBREVIATED_OPTIONS, STATE_OPTIONS } from '@constants/constants';

export function capitalize(str: string | null): string | null {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export const formatDisplayValue = (value: any): any => {
  if (typeof value === 'number') {
    return new Intl.NumberFormat('en-US').format(value);
  }
  return value;
};

export const matchPath = (paths: string[], path: string) => {
  if (paths.includes(path)) return true;
  return false;
};

export const getStateAbbreviation = (
  state_name: string | null
): string | undefined => {
  if (state_name) {
    const index = STATE_OPTIONS.indexOf(state_name);
    if (index !== -1) {
      return STATE_ABBREVIATED_OPTIONS[index];
    }
  }
  return '';
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
