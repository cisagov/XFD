// The data in this table is derived from the Vulnerability Scans Database,
// the [vuln_scans Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#vuln_scans-collection).

import {
  Entity,
  Column,
  PrimaryColumn,
  BaseEntity,
  ManyToMany,
  ManyToOne,
  JoinTable,
  OneToMany
} from 'typeorm';
import { Snapshot } from './snapshots';
import { Ip } from './ips';
import { Organization } from './organizations';
import { Cve } from './cves';
import { TicketEvent } from './ticket_events';

@Entity()
export class VulnScan extends BaseEntity {
  @PrimaryColumn()
  id: string;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // bugtraqId: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  certId: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cpe: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cveString: string | null;

  @ManyToOne((type) => Cve, (cve) => cve.vulnScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  cve: Cve;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvssBaseScore: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvssTemporalScore: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvssTemporalVector: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvssVector: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  description: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  exploitAvailable: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  exploitabilityEase: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // pluginFilename: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  ipString: string | null;

  @ManyToOne((type) => Ip, (ip) => ip.vulnScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  ip: Ip;

  @Column({ nullable: true })
  latest: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  owner: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  osvdbId: string | null;

  @ManyToOne((type) => Organization, (org) => org.vulnScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;

  @Column({ nullable: true, type: 'timestamp' })
  patchPublicationTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  cisaKnownExploited: Date | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  port: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  portProtocol: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  riskFactor: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  scriptVersion: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  seeAlso: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  service: string | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  severity: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  solution: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  source: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  synopsis: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  vulnDetectionTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  vulnPublicationTimestamp: Date | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  xref: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cwe: string | null;

  // @Column({ nullable: true })
  // exploitFrameworkMetasploit: boolean;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // metasploitName: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // edbId: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  bid: string | null;

  @Column({ nullable: true })
  exploitedByMalware: boolean;

  // @Column({ nullable: true })
  // exploitFrameworkCore: boolean;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // stigSeverity: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // iava: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // iavb: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // tra: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // msft: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // canvasPackage: string | null;

  // @Column({ nullable: true })
  // exploitFrameworkCanvas: boolean;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // secunia: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // agent: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // rhsa: string | null;

  // @Column({ nullable: true })
  // inTheNews: boolean;

  @Column({ nullable: true })
  thoroughTests: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvssScoreRationale: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // attachment: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'decimal'
  // })
  // vprScore: number | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // threatSourcesLast28: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // exploitCodeMaturity: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // threatIntensityLast28: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // ageOfVuln: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'decimal'
  // })
  // cvssV3ImpactScore: number | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // threatRecency: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // productCoverage: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvssScoreSource: string | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  cvss3BaseScore: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvss3Vector: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvss3TemporalVector: string | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  cvss3TemporalScore: number | null;

  // @Column({ nullable: true })
  // exploitedByNessus: boolean;

  // @Column({ nullable: true })
  // unsupportedByVendor: boolean;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // requiredKey: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'integer'
  // })
  // requiredPort: number | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // scriptCopyright: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // mskb: string | null;

  // @Column({
  //   nullable: true,
  //   type: 'varchar'
  // })
  // dependency: string | null;

  @Column({ nullable: true })
  assetInventory: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  pluginId: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  pluginModificationDate: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  pluginPublicationDate: Date | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  pluginName: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  pluginType: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  pluginFamily: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  fName: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  ciscoBugId: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  ciscoSa: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  pluginOutput: string | null;

  @ManyToMany((type) => Snapshot, (snapshot) => snapshot.vulnScans, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  snapshots: Snapshot[];

  @OneToMany((type) => TicketEvent, (event) => event.vulnScan, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  ticketEvents?: TicketEvent[];

  @Column({
    type: 'jsonb',
    default: {}
  })
  otherFindings: object;
}
