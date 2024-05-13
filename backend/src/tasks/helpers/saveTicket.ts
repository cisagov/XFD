import { plainToClass } from 'class-transformer';
import {
  Ticket,
  DL_Organization,
  Cidr,
  Location,
  connectToDatalake
} from '../../models';

export default async (ticket: Ticket): Promise<string> => {
  console.log(`Starting to save Ticket to datalake`);
  await connectToDatalake();
  const ticketUpdatedValues = Object.keys(ticket)
    .map((key) => {
      if (['id'].indexOf(key) > -1) return '';
      else if (key === 'organization') return 'organizationId';
      else if (key === 'ip') return 'ipId';
      else if (key === 'cve') return 'cveId';
      return ticket[key] !== null ? key : '';
    })
    .filter((key) => key !== '');
  const ticket_id: string = (
    await Ticket.createQueryBuilder()
      .insert()
      .values(ticket)
      .orUpdate({
        conflict_target: ['id'],
        overwrite: ticketUpdatedValues
      })
      .returning('id')
      .execute()
  ).identifiers[0].id;

  return ticket_id;
};
