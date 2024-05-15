import { plainToClass } from 'class-transformer';
import {
  TicketEvent,
  DL_Organization,
  Cidr,
  Location,
  connectToDatalake
} from '../../models';

export default async (ticket_event: TicketEvent): Promise<string> => {
  await connectToDatalake();
  const ticketEventUpdatedValues = Object.keys(ticket_event)
    .map((key) => {
      if (['eventTimestamp', 'action', 'ticket'].indexOf(key) > -1) return '';
      else if (key === 'vulnScan') return 'vulnScanId';
      return ticket_event[key] !== null ? key : '';
    })
    .filter((key) => key !== '');
  const ticket_event_id: string = (
    await TicketEvent.createQueryBuilder()
      .insert()
      .values(ticket_event)
      .orUpdate({
        conflict_target: ['eventTimestamp', 'action', 'ticketId'],
        overwrite: ticketEventUpdatedValues
      })
      .returning('id')
      .execute()
  ).identifiers[0].id;

  return ticket_event_id;
};
