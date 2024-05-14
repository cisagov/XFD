// The data in this table is derived from the Vulnerability Scans Database,
// the [tallies Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#tallies-collection).

import {
  Entity,
  Index,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  ManyToOne
} from 'typeorm';
import { Organization } from './organizations';
@Entity()
export class Tally extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    nullable: true,
    type: 'varchar',
    unique: true
  })
  @Index()
  acronym: string | null;

  @ManyToOne((type) => Organization, (org) => org.tallies, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;

  @Column({
    type: 'jsonb',
    default: {}
  })
  netscan1Counts: object;

  @Column({
    type: 'jsonb',
    default: {}
  })
  netscan2Counts: object;

  @Column({
    type: 'jsonb',
    default: {}
  })
  portscanCounts: object;

  @Column({
    type: 'jsonb',
    default: {}
  })
  vulnscanCounts: object;

  @Column({ nullable: true, type: 'timestamp' })
  updatedTimestamp: Date | null;
}
