// The data in this table is derived from the Vulnerability Scans Database,
// the [port_scans Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#port_scans-collection).

import {
  Entity,
  Column,
  PrimaryColumn,
  BaseEntity,
  ManyToMany,
  ManyToOne
} from 'typeorm';

import { Snapshot } from './snapshots';
import { Ip } from './ips';
import { Organization } from './organizations';
@Entity()
export class PortScan extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  ipString: string | null;

  @ManyToOne((type) => Ip, (ip) => ip.portScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  ip: Ip;

  @Column()
  latest: boolean;

  @Column({
    nullable: true,
    type: 'integer'
  })
  port: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  protocol: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  reason: string | null;

  @Column({
    type: 'jsonb',
    default: {}
  })
  service: object;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  serviceName: string | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  serviceConfidence: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  serviceMethod: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  source: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  state: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  timeScanned: Date | null;

  @ManyToMany((type) => Snapshot, (snapshot) => snapshot.portScans, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  snapshots: Snapshot[];

  @ManyToOne((type) => Organization, (org) => org.portScans, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;
}
