// The data in this table is derived from IP addresses supplied by the
// CyHy stakeholders.

import {
  Entity,
  Index,
  Column,
  PrimaryColumn,
  BaseEntity,
  ManyToOne
} from 'typeorm';
import { Organization } from './organizations';
import { Ip } from './ips';
// TODO Determine if this should be merged with the ips column
@Entity()
@Index(['ip'])
export class Host extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  ipString: string | null;

  @ManyToOne((type) => Ip, (ip) => ip.hosts, {
    onDelete: 'SET NULL',
    onUpdate: 'CASCADE'
  })
  ip: Ip;

  @Column({ nullable: true, type: 'timestamp' })
  updatedTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  latestNetscan1Timestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  latestNetscan2Timestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  latestVulnscanTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  latestPortscanTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  latestScanCompletionTimestamp: Date | null;

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

  @Column({
    nullable: true,
    type: 'integer'
  })
  priority: number | null;

  @Column({ nullable: true, type: 'timestamp' })
  nextScanTimestamp: Date | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  rand: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  currStage: string | null;

  @Column({ nullable: true })
  hostLive: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  hostLiveReason: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  status: string | null;

  @ManyToOne((type) => Organization, (org) => org.hosts, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;
}
