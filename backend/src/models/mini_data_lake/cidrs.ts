import {
  Entity,
  Index,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  BaseEntity,
  ManyToMany,
  JoinTable,
  UpdateDateColumn
} from 'typeorm';

import { Organization } from './organizations';
@Entity()
export class Cidr extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @CreateDateColumn()
  createdDate: Date;

  @Index()
  @Column({
    nullable: true,
    type: 'inet',
    unique: true
  })
  network: string | null;

  @Column({
    nullable: true,
    type: 'inet'
  })
  startIp: string | null;

  @Column({
    nullable: true,
    type: 'inet'
  })
  endIp: string | null;

  @Column({ nullable: true })
  retired: boolean;

  @UpdateDateColumn()
  updatedAt: Date | null;

  @ManyToMany((type) => Organization, (org) => org.cidrs, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  organizations: Organization[];
}
