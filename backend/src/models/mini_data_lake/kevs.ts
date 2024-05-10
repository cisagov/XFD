// The data in this table is derived from the
// [JSON feed](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json)
// of the [CISA Known Exploited Vulnerabilities
// Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog).

import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  OneToMany
} from 'typeorm';
import { Ticket } from './tickets';
@Entity()
export class Kev extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    nullable: true,
    type: 'varchar',
    unique: true
  })
  cve: string | null;

  @Column({ nullable: true })
  knownRansomware: boolean;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  vendorProject: string | null;
  @Column({
    nullable: true,
    type: 'varchar'
  })
  product: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  vulnerabilityName: string | null;

  @Column({
    nullable: true,
    type: 'timestamp'
  })
  dateAdded: Date | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  shortDescription: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  requiredAction: string | null;

  @Column({ nullable: true, type: 'timestamp' })
  dueDate: Date | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  notes: string | null;

  @OneToMany((type) => Ticket, (ticket) => ticket.kev, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  tickets: Ticket[];
}
