// The data in this table is derived from IP addresses supplied by the
// CyHy stakeholders.

import { DirectConnect } from 'aws-sdk';
import { toInteger } from 'lodash';
import { Snapshot } from './snapshots';
import {
  Entity,
  Column,
  PrimaryColumn,
  BaseEntity,
  ManyToMany,
  ManyToOne
} from 'typeorm';

import { Ip } from './ips';
import { Organization } from './organizations';

@Entity()
export class HostScan extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  ipString: string | null;

  @ManyToOne((type) => Ip, (ip) => ip.hostScans, {
    onDelete: 'SET NULL',
    onUpdate: 'CASCADE'
  })
  ip: Ip;

  @Column({
    nullable: true,
    type: 'integer'
  })
  accuracy: number | null;

  @Column({
    type: 'jsonb',
    default: []
  })
  classes: Object[];

  @Column({
    nullable: true,
    type: 'varchar'
  })
  hostname: string | null;

  @Column({ nullable: true })
  latest: boolean;

  @Column({
    nullable: true,
    type: 'integer'
  })
  line: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  name: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  source: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  scanTimestamp: Date | null;

  @ManyToMany((type) => Snapshot, (snapshot) => snapshot.hostScans, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  snapshots: Snapshot[];

  @ManyToOne((type) => Organization, (org) => org.hostScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;
}
