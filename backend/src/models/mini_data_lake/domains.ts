// The data in this table is derived from domains collected by our
// [gatherer](https://github.com/cisagov/gatherer), which pulls in
// domains from Cyber Hygiene and the GSA.  NOTE: More details may be
// available in the GitHub
// [README](https://github.com/cisagov/cyhy-ct-logs/blob/initial/README.md)
// documents for [gatherer](https://github.com/cisagov/gatherer) and
// [saver](https://github.com/cisagov/saver).

import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  BaseEntity,
  OneToMany,
  ManyToMany,
  ManyToOne,
  Unique
} from 'typeorm';

import { Organization } from './organizations';
import { CertScan } from './cert_scans';
import { PrecertScan } from './precert_scans';
import { Ip } from './ips';
import { SslyzeScan } from './sslyze_scan';
import { TrustymailScan } from './trustymail_scans';

@Entity()
@Unique(['domain'])
export class Domain extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @ManyToOne((type) => Organization, (organization) => organization.domains, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  organization: Organization;

  @ManyToOne((type) => Ip, (ip) => ip.domains, {
    onDelete: 'SET NULL',
    onUpdate: 'CASCADE'
  })
  ip: Ip;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  ipString: string | null;

  @CreateDateColumn()
  createdAt: Date;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  domain: string | null;

  @Column({ nullable: true })
  retired: boolean;

  @Column({ nullable: true })
  falsePositive: boolean;

  @Column({ nullable: true })
  identifiedFromIp: boolean;

  @ManyToOne((type) => Domain, (dom) => dom.subDomains, {
    onDelete: 'CASCADE',
    nullable: true
  })
  rootDomain: Domain;

  @OneToMany((type) => Domain, (dom) => dom.rootDomain, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  subDomains: Domain[];

  @ManyToMany((type) => CertScan, (cert_scan) => cert_scan.domains, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  certScans: CertScan[];

  @ManyToMany((type) => PrecertScan, (precert_scan) => precert_scan.domains, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  precertScans: PrecertScan[];

  @OneToMany((type) => SslyzeScan, (sslyze_scan) => sslyze_scan.domain, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  sslyzeScans: SslyzeScan[];

  @OneToMany(
    (type) => TrustymailScan,
    (trustymail_scan) => trustymail_scan.domain,
    {
      onDelete: 'CASCADE',
      onUpdate: 'CASCADE'
    }
  )
  trustymailScans: TrustymailScan[];
}
