// The data in this collection is derived from the Vulnerability Scans Database,
// the [snapshots Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#snapshots-collection).

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

import { HostScan } from './host_scans';
import { PortScan } from './port_scans';
import { Report } from './reports';
import { Organization } from './organizations';
import { Ticket } from './tickets';
import { VulnScan } from './vuln_scans';
@Entity()
export class Snapshot extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  cvssAverageAll: number | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  cvssAverageVulnerable: number | null;

  @Column({ nullable: true, type: 'timestamp' })
  startTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  endTimestamp: Date | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  hostCount: number | null;

  @Column({ nullable: true, type: 'timestamp' })
  updatedTimestamp: Date | null;

  @Column({ nullable: true })
  latest: boolean;

  @Column('varchar', { array: true, default: [] })
  networks: string[];

  @ManyToOne((type) => Organization, (org) => org.snapshots, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;

  @Column({
    nullable: true,
    type: 'integer'
  })
  portCount: number | null;

  @Column({
    type: 'jsonb',
    default: {}
  })
  services: object;

  @Column({
    nullable: true,
    type: 'integer'
  })
  uniqueOsCount: number | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  uniquePortCount: number | null;

  @Column({
    type: 'jsonb',
    default: {}
  })
  uniqueVulnerabilities: object;

  @Column({
    nullable: true,
    type: 'integer'
  })
  vulnHostCount: number | null;

  @Column({
    type: 'jsonb',
    default: {}
  })
  vulnerabilities: object;

  @ManyToMany((type) => HostScan, (hostscan) => hostscan.snapshots, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  hostScans: HostScan[];

  @ManyToMany((type) => PortScan, (portscan) => portscan.snapshots, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  portScans: PortScan[];

  @OneToMany((type) => Report, (report) => report.snapshot, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  reports: Report[];

  @ManyToMany((type) => Ticket, (ticket) => ticket.snapshots, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  tickets: Ticket[];

  @ManyToMany((type) => VulnScan, (vuln_scan) => vuln_scan.snapshots, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  vulnScans: VulnScan[];

  @ManyToMany((type) => Snapshot, (snapshot) => snapshot.parents, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  children: Snapshot[];

  @ManyToMany((type) => Snapshot, (snapshot) => snapshot.children, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  parents: Snapshot[];
}
