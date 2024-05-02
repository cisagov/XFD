import {
  BaseEntity,
  Column,
  CreateDateColumn,
  Entity,
  Index,
  ManyToMany,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
  Relation
} from 'typeorm';
import { Domain, OrganizationTag, Role, Scan, ScanTask, User } from './index';

export interface PendingDomain {
  name: string;
  token: string;
}

@Entity()
export class Organization extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Index({ unique: true })
  @Column({
    nullable: true,
    unique: true
  })
  acronym: string;

  @Column()
  name: string;

  @Column('varchar', { array: true })
  rootDomains: string[];

  @Column('varchar', { array: true })
  ipBlocks: string[];

  @Column()
  isPassive: boolean;

  @OneToMany((type) => Domain, (domain) => domain.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  domains: Relation<Domain>[];

  @Column('jsonb', { default: '[]' })
  pendingDomains: Relation<PendingDomain>[];

  @OneToMany((type) => Role, (role) => role.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  userRoles: Relation<Role>[];

  /**
   * Corresponds to "organization" property of ScanTask.
   * Deprecated, replaced by "allScanTasks" property.
   */
  @OneToMany((type) => ScanTask, (scanTask) => scanTask.organization, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  scanTasks: Relation<ScanTask>[];

  /**
   * Corresponds to "organizations" property of ScanTask.
   */
  @ManyToMany((type) => ScanTask, (scanTask) => scanTask.organizations, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  allScanTasks: Relation<ScanTask>[];

  @ManyToMany((type) => Scan, (scan) => scan.organizations, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  granularScans: Relation<Scan>[];

  @ManyToMany((type) => OrganizationTag, (tag) => tag.organizations, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  tags: Relation<OrganizationTag>[];

  /**
   * The organization's parent organization, if any.
   * Organizations without a parent organization are
   * shown to users as 'Organizations', while organizations
   * with a parent organization are shown to users as 'Teams'
   */
  @ManyToOne((type) => Organization, (org) => org.children, {
    onDelete: 'CASCADE',
    nullable: true
  })
  parent: Relation<Organization>;

  @OneToMany((type) => Organization, (org) => org.parent, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  children: Relation<Organization>[];

  @ManyToOne((type) => User, {
    onDelete: 'SET NULL',
    onUpdate: 'CASCADE'
  })
  createdBy: Relation<User>;

  @Column({
    nullable: true
  })
  country: string;

  @Column({
    nullable: true
  })
  state: string;

  @Column({
    nullable: true
  })
  regionId: string;

  @Column({
    nullable: true
  })
  stateFips: number;

  @Column({
    nullable: true
  })
  stateName: string;

  @Column({
    nullable: true
  })
  county: string;

  @Column({
    nullable: true
  })
  countyFips: number;

  @Column({
    nullable: true
  })
  type: string;
}
