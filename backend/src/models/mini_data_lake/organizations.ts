// The data in this table is derived from the Vulnerability Scans Database,
// the [requests Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#requests-collection).

import {
  Entity,
  Index,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  OneToMany,
  ManyToMany,
  ManyToOne,
  CreateDateColumn,
  UpdateDateColumn
} from 'typeorm';
import { Domain } from './domains';
import { Ip } from './ips';
import { Location } from './locations';
import { Contact } from './contacts';
import { Tag } from './tag';
import { Sector } from './sectors';
import { Report } from './reports';
import { SslyzeScan } from './sslyze_scan';
import { Snapshot } from './snapshots';
import { Tally } from './tallies';
import { TrustymailScan } from './trustymail_scans';
import { VulnScan } from './vuln_scans';
import { Cidr } from './cidrs';
import { HostScan } from './host_scans';
import { Host } from './hosts';
import { Ticket } from './tickets';
import { PortScan } from './port_scans';
@Entity()
export class Organization extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  name: string | null;

  @Column({
    nullable: true,
    type: 'varchar',
    unique: true
  })
  @Index()
  acronym: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  enrolledInVsTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  periodStartVsTimestamp: Date | null;

  @CreateDateColumn()
  createdDate: Date;

  @UpdateDateColumn()
  updatedDate: Date | null;

  @Column({ nullable: true })
  retired: boolean;

  @Column({ nullable: true })
  peReportOn: boolean;

  @Column({ nullable: true })
  pePremium: boolean;

  @Column({ nullable: true })
  peDemo: boolean;

  @Column({ nullable: true })
  peRunScans: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  type: string | null;

  @Column({ nullable: true })
  stakeholder: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  reportPeriod: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  initStage: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  scheduler: string | null;

  @Column('varchar', { array: true, default: [], nullable: true })
  reportTypes: string[] | null;

  @Column('varchar', { array: true, default: [], nullable: true })
  scanTypes: string[] | null;

  @Column({
    nullable: true,
    type: 'jsonb',
    default: []
  })
  scanWindows: Object[] | null;

  @Column({
    nullable: true,
    type: 'jsonb',
    default: []
  })
  scanLimits: Object[] | null;

  @OneToMany((type) => Domain, (domain) => domain.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  domains: Domain[];

  @OneToMany((type) => Ip, (ip) => ip.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  ips: Ip[];

  @OneToMany((type) => Ticket, (ticket) => ticket.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  tickets: Ticket[];

  @ManyToOne((type) => Location, (location) => location.organizations, {
    onDelete: 'CASCADE',
    nullable: true
  })
  location: Location;

  @ManyToMany((type) => Contact, (contact) => contact.organizations, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  contacts: Contact[];

  @ManyToMany((type) => Tag, (tag) => tag.organizations, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  tags: Tag[];

  @ManyToMany((type) => Sector, (sector) => sector.organizations, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  sectors: Sector[];

  @ManyToMany((type) => Cidr, (cidr) => cidr.organizations, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  cidrs: Cidr[];

  @ManyToOne((type) => Organization, (org) => org.children, {
    onDelete: 'CASCADE',
    nullable: true
  })
  parent: Organization;

  @OneToMany((type) => Organization, (org) => org.parent, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  children: Organization[];

  @OneToMany((type) => Report, (report) => report.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  reports: Report[];

  @OneToMany((type) => SslyzeScan, (sslyze) => sslyze.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  sslyzeScans: SslyzeScan[];

  @OneToMany((type) => Snapshot, (snapshot) => snapshot.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  snapshots: Snapshot[];

  @OneToMany((type) => Tally, (tally) => tally.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  tallies: Tally[];

  @OneToMany(
    (type) => TrustymailScan,
    (trustymail_scan) => trustymail_scan.organization,
    {
      onDelete: 'CASCADE',
      onUpdate: 'CASCADE'
    }
  )
  trustymailScans: TrustymailScan[];

  @OneToMany((type) => VulnScan, (vuln_scan) => vuln_scan.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  vulnScans: VulnScan[];

  @OneToMany((type) => HostScan, (host_scan) => host_scan.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  hostScans: HostScan[];

  @OneToMany((type) => Host, (host) => host.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  hosts: Host[];

  @OneToMany((type) => PortScan, (port_scan) => port_scan.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  portScans: PortScan[];
}
