import {
  Entity,
  Index,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  BaseEntity,
  ManyToMany,
  JoinTable,
  Relation
} from 'typeorm';

import { Request } from './requests';
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
    type: 'cidr',
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

  @ManyToMany((type) => Request, (request) => request.cidrs, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  requests: Relation<Request>[];

  @ManyToMany((type) => Organization, (org) => org.cidrs, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable()
  organizations: Relation<Organization>[];
}
