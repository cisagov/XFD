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

import { Organization } from './organizations';

@Entity()
export class WasFinding extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  webappId: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  wasOrgId: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  owaspCategory: string | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  severity: number | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  timesDetected: number | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  baseScore: number | null;

  @Column({
    nullable: true,
    type: 'decimal'
  })
  temporalScore: number | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  fstatus: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  lastDetected: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  firstDetected: Date | null;

  @Column({ nullable: true })
  isRemediated: boolean;

  @Column({ nullable: true })
  potential: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  webappUrl: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  webappName: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  name: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  cvssV3AttackVector: string | null;

  @Column('int', { array: true, default: [] })
  cweList: number[];

  @Column({
    type: 'jsonb',
    default: []
  })
  wascList: object;

  @Column({ nullable: true, type: 'timestamp' })
  lastTested: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  fixedDate: Date | null;

  @Column({ nullable: true })
  isIgnored: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  url: string | null;

  @Column({
    nullable: true,
    type: 'integer'
  })
  qid: number | null;

  @ManyToOne((type) => Organization, (org) => org.wasFindings, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;
}
