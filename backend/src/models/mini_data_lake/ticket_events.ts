// The data in this table is derived from the Vulnerability Scans Database,
// the [tickets Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#tickets-collection).

import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  ManyToOne,
  Unique
} from 'typeorm';

import { Ticket } from './tickets';
import { VulnScan } from './vuln_scans';

@Entity()
@Unique(['eventTimestamp', 'ticket', 'action'])
export class TicketEvent extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  reference: string | null;

  @ManyToOne((type) => VulnScan, (vuln_scan) => vuln_scan.ticketEvents, {
    onDelete: 'CASCADE',
    nullable: true
  })
  vulnScan: VulnScan;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  action: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  reason: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  eventTimestamp: Date | null;

  @Column({
    type: 'jsonb',
    default: []
  })
  delta: Object[];

  @ManyToOne((type) => Ticket, (ticket) => ticket.ticketEvents, {
    onDelete: 'CASCADE',
    nullable: true
  })
  ticket: Ticket;
}
