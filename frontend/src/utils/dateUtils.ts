import { format, fromZonedTime } from 'date-fns-tz';

export function formReadableDate(date: string) {
  const parsedDate = new Date(date);
  return format(parsedDate, 'yyyy-MM-dd HH:mm');
}

export function formatDate(dateString?: string | null): string {
  if (!dateString) return '';
  return new Date(dateString).toISOString().split('T')[0];
}

export function humanReadableDate(date: string) {
  const parsedDate = new Date(date);
  return format(parsedDate, 'LLL dd, yyyy hh:mm a');
}

// Convert an ET date string to UTC
export function toUTC(date: string) {
  const etDate = fromZonedTime(date, 'America/New_York');
  const utcDate = etDate.toISOString();
  return utcDate;
}

// Convert a UTC date string to ET
export function toEST(date: string) {
  const parsedDate = new Date(date);
  const etDate = parsedDate.toLocaleString('en-US', {
    timeZone: 'America/New_York'
  });
  return etDate;
}

export function formatShortDate(
  dateInput: string | Date | null | undefined
): string {
  if (!dateInput) return '';
  const dateObj = new Date(dateInput);
  if (Number.isNaN(dateObj.getTime())) return '';
  return dateObj.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

export function formatRange(
  start?: string | Date | null | undefined,
  end?: string | Date | null | undefined
): string {
  const startStr = formatShortDate(start);
  const endStr = formatShortDate(end);
  if (!startStr && !endStr) return 'No Dates Available';
  // Ensures only end date is shown per CRASM-3140
  if (startStr && endStr) return `${endStr}`;
  return startStr || endStr;
}

export function enrolledWithinTwoWeeks(timestamp?: string | null): boolean {
  if (!timestamp) return false;

  const enrolledDate = new Date(timestamp);
  if (isNaN(enrolledDate.getTime())) return false;

  const now = new Date();
  const twoWeeksInMs = 14 * 24 * 60 * 60 * 1000;

  return now.getTime() - enrolledDate.getTime() <= twoWeeksInMs;
}
