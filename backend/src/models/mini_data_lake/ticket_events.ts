// The data in this table is derived from the Vulnerability Scans Database,
// the [tickets Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#tickets-collection).

import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  ManyToOne
} from 'typeorm';

import { Ticket } from './tickets';

@Entity()
export class TicketEvent extends BaseEntity {
  @PrimaryGeneratedColumn()
  id: string;

  @Column({
    nullable: true,
    type: 'varchar',
    unique: true
  })
  reference: string | null;

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
