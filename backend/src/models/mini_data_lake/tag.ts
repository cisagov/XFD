// The data in this collection is derived from

import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  ManyToMany,
  JoinTable
} from 'typeorm';

import { Organization } from './organizations';
@Entity()
export class Tag extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    nullable: true,
    type: 'varchar',
    unique: true
  })
  name: string | null;

  @ManyToMany((type) => Organization, (org) => org.tags, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  organizations: Organization[];
}
