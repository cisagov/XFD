// The data in this collection is derived from domain names collected by
// our [gatherer](https://github.com/cisagov/gatherer), which pulls in
// domains from Cyber Hygiene and the GSA.  NOTE: More details may be
// available in the GitHub
// [README](https://github.com/nabla-c0d3/sslyze/blob/master/README.md)
// document for [SSLyze](https://github.com/nabla-c0d3/sslyze).

import { Entity, Column, PrimaryColumn, BaseEntity, ManyToOne } from 'typeorm';

import { Domain } from './domains';
import { Organization } from './organizations';

@Entity()
export class SslyzeScan extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @ManyToOne((type) => Organization, (org) => org.sslyzeScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;

  @ManyToOne((type) => Domain, (domain) => domain.sslyzeScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  domain: Domain;

  @Column({ nullable: true })
  all_forward_secrecy: boolean;

  @Column({ nullable: true })
  allRc4: boolean;

  @Column({ nullable: true })
  any_3des: boolean;

  @Column({ nullable: true })
  anyForwardSecrecy: boolean;

  @Column({ nullable: true })
  anyRc4: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  errors: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  highestConstructedIssuer: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  highestServedIssuer: string | null;

  @Column({ nullable: true })
  isSymantecCert: boolean;

  @Column({
    nullable: true,
    type: 'integer'
  })
  keyLength: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  keyType: string | null;

  @Column({ nullable: true })
  latest: boolean;

  @Column({ nullable: true, type: 'timestamp' })
  scanTimestamp: Date | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  scannedHostname: string | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  scannedPort: number | null;

  @Column({ nullable: true })
  sha1InConstrustedChain: boolean;

  @Column({ nullable: true })
  sha1InServedChain: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  signatureAlgorithm: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  symantecDistrustDate: string | null;

  @Column({ nullable: true })
  sslv2: boolean;

  @Column({ nullable: true })
  sslv3: boolean;

  @Column({ nullable: true })
  starttlsSmtp: boolean;

  @Column({ nullable: true })
  tlsv1_0: boolean;

  @Column({ nullable: true })
  tlsv1_1: boolean;

  @Column({ nullable: true })
  tlsv1_2: boolean;
}
