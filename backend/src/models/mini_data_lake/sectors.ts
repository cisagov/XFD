// The data in this collection is derived from the requests collection.

import {
  Entity,
  Index,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  ManyToMany,
  JoinTable
} from 'typeorm';
import { Organization } from './organizations';
@Entity()
export class Sector extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  name: string | null;

  @Column({
    nullable: true,
    type: 'varchar',
    unique: true
  })
  @Index()
  acronym: string | null;

  @Column({ nullable: true })
  retired: boolean;

  @ManyToMany((type) => Organization, (org) => org.sectors, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  organizations: Organization[];
}
