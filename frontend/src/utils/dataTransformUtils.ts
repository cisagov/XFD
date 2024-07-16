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
