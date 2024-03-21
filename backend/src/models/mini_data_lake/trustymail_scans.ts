// The data in this collection is derived from domain names collected by
// our [gatherer](https://github.com/cisagov/gatherer), which pulls in
// domains from Cyber Hygiene and the GSA.  NOTE: More details may be
// available in the GitHub
// [README](https://github.com/cisagov/trustymail/blob/develop/README.md)
// document for [trustymail](https://github.com/cisagov/trustymail).

import { Entity, Column, PrimaryColumn, BaseEntity, ManyToOne } from 'typeorm';
import { Organization } from './organizations';
import { Domain } from './domains';

@Entity()
export class TrustymailScan extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @ManyToOne((type) => Organization, (org) => org.trustymailScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;

  @ManyToOne((type) => Domain, (domain) => domain.trustymailScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  domain: Domain;

  @Column({
    type: 'jsonb',
    default: []
  })
  aggregateReportUris: Object[];

  @Column({
    nullable: true,
    type: 'varchar'
  })
  debugInfo: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  dmarcPolicy: string | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  dmarcPolicyPercentage: number | null;

  @Column({ nullable: true })
  dmarcRecord: boolean;

  @Column({ nullable: true })
  dmarcRecordBaseDomain: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  dmarcResults: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  dmarcResultsBaseDomain: string | null;

  @Column({ nullable: true })
  domainSupportsSmtp: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  domainSupportsSmtpResults: string | null;

  @Column({ nullable: true })
  domainSupportsStarttls: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  domainSupportsStarttlsResults: string | null;

  @Column({
    type: 'jsonb',
    default: []
  })
  forensicReportUris: Object[];

  @Column({ nullable: true })
  hasAggregateReportUri: boolean;

  @Column({ nullable: true })
  hasForensicReportUri: boolean;

  @Column({ nullable: true })
  isBaseDomain: boolean;

  @Column({ nullable: true })
  latest: boolean;

  @Column({ nullable: true })
  live: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  mailServerPortsTested: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  mailServers: string | null;

  @Column({ nullable: true })
  mxRecord: boolean;

  @Column({ nullable: true, type: 'timestamp' })
  scanTimestamp: Date | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  spfResults: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  syntaxErrors: string | null;

  @Column({ nullable: true })
  validDmarc: boolean;

  @Column({ nullable: true })
  validDmarcBaseDomain: boolean;

  @Column({ nullable: true })
  validSpf: boolean;
}
