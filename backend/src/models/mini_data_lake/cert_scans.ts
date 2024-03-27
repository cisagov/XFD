// The data in this table is derived from the Vulnerability Scans Database,
// the [certs Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#certs-collection).

import {
  Entity,
  Column,
  PrimaryColumn,
  BaseEntity,
  ManyToMany,
  JoinTable
} from 'typeorm';

import { Domain } from './domains';

@Entity()
export class CertScan extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  issuer: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  expirationTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  certStartTimestamp: Date | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  pem: string | null;

  @Column({ nullable: true })
  sctExists: boolean;

  @Column({ nullable: true, type: 'timestamp' })
  sctOrNotBefore: Date | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  serial: string | null;

  @ManyToMany((type) => Domain, (domain) => domain.certScans, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  domains: Domain[];
}
