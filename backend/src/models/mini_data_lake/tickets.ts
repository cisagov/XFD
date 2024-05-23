// The data in this table is derived from the Vulnerability Scans Database,
// the [tickets Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#tickets-collection).

import {
  Entity,
  Column,
  PrimaryColumn,
  BaseEntity,
  OneToMany,
  ManyToMany,
  ManyToOne,
  JoinTable
} from 'typeorm';

import { Organization } from './organizations';
import { Kev } from './kevs';
import { Ip } from './ips';
import { Snapshot } from './snapshots';
import { TicketEvent } from './ticket_events';
import { Cve } from './cves';
@Entity()
export class Ticket extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cveString: string | null;

  @ManyToOne((type) => Cve, (cve) => cve.tickets, {
    onDelete: 'CASCADE',
    nullable: true
  })
  cve: Cve;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  cvss_base_score: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvss_version: string | null;

  @ManyToOne((type) => Kev, (kev) => kev.tickets, {
    onDelete: 'CASCADE',
    nullable: true
  })
  kev: Kev;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  vulnName: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvssScoreSource: string | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  cvssSeverity: number | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  vprScore: number | null;

  @Column({ nullable: true })
  falsePositive: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  ipString: string | null;

  @ManyToOne((type) => Ip, (ip) => ip.tickets, {
    onDelete: 'CASCADE',
    nullable: true
  })
  ip: Ip;

  @Column({ nullable: true, type: 'timestamp' })
  updatedTimestamp: Date | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  locationLongitude: number | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  locationLatitude: number | null;

  @Column({ nullable: true })
  foundInLatestHostScan: boolean;

  @ManyToOne((type) => Organization, (org) => org.tickets, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;

  @Column({
    nullable: true,
    type: 'integer'
  })
  vulnPort: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  portProtocol: string | null;

  @Column({ nullable: true })
  snapshotsBool: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  vulnSource: string | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  vulnSourceId: number | null;

  @Column({ nullable: true, type: 'timestamp' })
  closedTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  openedTimestamp: Date | null;

  @ManyToMany((type) => Snapshot, (snapshot) => snapshot.tickets, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  snapshots: Snapshot[];

  @OneToMany((type) => TicketEvent, (ticket_event) => ticket_event.ticket, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  ticketEvents: TicketEvent[];
}
