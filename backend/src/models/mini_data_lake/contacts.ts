// The data in this table is derived from the Vulnerability Scans Database,
// the [requests Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#requests-collection).

import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  ManyToMany,
  Unique,
  JoinTable
} from 'typeorm';
import { Organization } from './organizations';
@Entity()
@Unique(['name', 'email', 'type'])
export class Contact extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  name: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  email: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  phoneNumber: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  type: string | null;

  @Column({ nullable: true })
  retired: boolean;

  @ManyToMany((type) => Organization, (org) => org.contacts, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  organizations: Organization[];
}
