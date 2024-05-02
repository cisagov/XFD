import {
  BaseEntity,
  Column,
  Entity,
  ManyToMany,
  PrimaryGeneratedColumn,
  Relation,
  Unique
} from 'typeorm';
import { Cve } from './cve';

@Entity()
@Unique(['name', 'version', 'vendor'])
export class Cpe extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column()
  version: string;

  @Column()
  vendor: string;

  @Column()
  lastSeenAt: Date;

  @ManyToMany(() => Cve, (cve) => cve.cpes)
  cves: Relation<Cve>[];
}
