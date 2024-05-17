import { format, fromZonedTime } from 'date-fns-tz';

export function formReadableDate(date: string) {
  const parsedDate = new Date(date);
  return format(parsedDate, 'yyyy-MM-dd HH:mm');
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
